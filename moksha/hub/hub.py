# This file is part of Moksha.
# Copyright (C) 2008-2010  Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors: Luke Macken <lmacken@redhat.com>


import os
import sys

# Look in the current directory for egg-info
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

import signal
import pkg_resources
import logging

from moksha.hub.reactor import reactor

from tg import config
from orbited import json
from paste.deploy import appconfig
from twisted.internet.error import ReactorNotRunning

from moksha.lib.helpers import trace, defaultdict, get_moksha_config_path, get_moksha_appconfig
from moksha.hub.amqp import AMQPHub
from moksha.hub.stomp import StompHub

log = logging.getLogger('moksha.hub')

_hub = None

class MokshaHub(StompHub, AMQPHub):

    topics = None # {topic_name: [callback,]}

    def __init__(self, topics=None):
        global config
        self.amqp_broker = config.get('amqp_broker', None)
        self.stomp_broker = config.get('stomp_broker', None)

        # If we're running outside of middleware and hub, load config
        if not self.amqp_broker and not self.stomp_broker:
            config = get_moksha_appconfig()
            self.amqp_broker = config.get('amqp_broker', None)
            self.stomp_broker = config.get('stomp_broker', None)

        if self.amqp_broker and self.stomp_broker:
            log.warning("Running with both a STOMP and AMQP broker. "
                        "This mode is experimental and may or may not work")

        if not self.topics:
            self.topics = defaultdict(list)

        if topics:
            for topic, callbacks in topics.iteritems():
                if not isinstance(callbacks, list):
                    callbacks = [callbacks]
                for callback in callbacks:
                    self.topics[topic].append(callback)

        if self.amqp_broker:
            AMQPHub.__init__(self, self.amqp_broker,
                             username=config.get('amqp_broker_user', 'guest'),
                             password=config.get('amqp_broker_pass', 'guest'),
                             ssl=config.get('amqp_broker_ssl', False))

        if self.stomp_broker:
            log.info('Initializing STOMP support')
            StompHub.__init__(self, self.stomp_broker,
                              port=config.get('stomp_port', 61613),
                              username=config.get('stomp_user', 'guest'),
                              password=config.get('stomp_pass', 'guest'),
                              topics=self.topics.keys())

    def send_message(self, topic, message, jsonify=True):
        """ Send a message to a specific topic.

        :topic: A topic or list of topics to send the message to.
        :message: The message body.  Can be a string, list, or dict.
        :jsonify: To automatically encode non-strings to JSON

        """
        if not isinstance(topic, list):
            topics = [topic]
        else:
            topics = topic
        for topic in topics:
            if jsonify:
                message = json.encode(message)
            if self.amqp_broker:
                AMQPHub.send_message(self, topic, message, routing_key=topic)
            elif self.stomp_broker:
                StompHub.send_message(self, topic, message)

    def close(self):
        if self.amqp_broker:
            try:
                AMQPHub.close(self)
            except Exception, e:
                log.warning('Exception when closing AMQPHub: %s' % str(e))

    def watch_topic(self, topic, callback):
        """
        This method will cause the specified `callback` to be executed with
        each message that goes through a given topic.
        """
        log.debug('watch_topic(%s)' % locals())
        if len(self.topics[topic]) == 0:
            if self.stomp_broker:
                self.subscribe(topic)
        self.topics[topic].append(callback)

    def consume_amqp_message(self, message):
        self.message_accept(message)
        try:
            topic = message.get('delivery_properties').routing_key
        except AttributeError:
            # If we receive an AMQP message without a toipc, don't proxy it to STOMP
            return

        if self.stomp_broker:
            StompHub.send_message(self, topic.encode('utf8'),
                                  message.body.encode('utf8'))

    def consume_stomp_message(self, message):
        topic = message['headers'].get('destination')
        if not topic:
            log.debug("Got message without a topic: %r" % message)
            return

        # FIXME: only do this if the consumer wants it `jsonified`
        try:
            body = json.decode(message['body'])
        except Exception, e:
            log.warning('Cannot decode message from JSON: %s' % e)
            #body = {}
            body = message['body']

        # feed all of our consumers
        for callback in self.topics.get(topic, []):
            reactor.callInThread(callback, {'body': body, 'topic': topic})


class CentralMokshaHub(MokshaHub):
    """
    The Moksha Hub is responsible for initializing all of the Hooks,
    AMQP queues, exchanges, etc.
    """
    producers = None # [<Producer>,]

    def __init__(self):
        log.info('Loading the Moksha Hub')
        self.topics = defaultdict(list)
        self.__init_consumers()

        MokshaHub.__init__(self)

        if self.amqp_broker:
            self.__init_amqp()

        self.__run_consumers()
        self.__init_producers()

    def __init_amqp(self):
        # Ok this looks odd at first.  I think this is only used when we are briding stomp/amqp,
        # Since each producer and consumer opens up their own AMQP connections anyway
        if self.stomp_broker:
            log.debug("Initializing local AMQP queue...")
            self.server_queue_name = 'moksha_hub_' + self.session.name
            self.queue_declare(queue=self.server_queue_name, exclusive=True)
            self.exchange_bind(self.server_queue_name, binding_key='#')
            self.local_queue_name = 'moksha_hub'
            self.local_queue = self.session.incoming(self.local_queue_name)
            self.message_subscribe(queue=self.server_queue_name,
                                   destination=self.local_queue_name)
            self.local_queue.start()
            self.local_queue.listen(self.consume_amqp_message)

    def __init_consumers(self):
        """ Initialize all Moksha Consumer objects """
        log.info('Loading Consumers')
        for consumer in pkg_resources.iter_entry_points('moksha.consumer'):
            c_class = consumer.load()
            log.info("%s consumer is watching the %r topic" % (
                     c_class.__name__, c_class.topic))
            self.topics[c_class.topic].append(c_class)

    def __run_consumers(self):
        """ Instantiate the consumers """
        self.consumers = []
        for topic in self.topics:
            for i, consumer in enumerate(self.topics[topic]):
                c = consumer()
                self.consumers.append(c)
                self.topics[topic][i] = c.consume

    def __init_producers(self):
        """ Initialize all producers (aka data streams) """
        log.info('Loading Producers')
        self.producers = []
        for entry in ('moksha.producer', 'moksha.stream'):
            for producer in pkg_resources.iter_entry_points(entry):
                producer_class = producer.load()
                log.info('Loading %s producer' % producer_class.__name__)
                producer_obj = producer_class()
                self.producers.append(producer_obj)

    @trace
    def create_topic(self, topic):
        if self.amqp_broker:
            AMQPHub.create_queue(topic)

        # @@ remove this when we keep track of this in a DB
        if topic not in self.topics:
            self.topics[topic] = []

    def stop(self):
        log.debug("Stopping the CentralMokshaHub")
        MokshaHub.close(self)
        if self.producers:
            for producer in self.producers:
                log.debug("Stopping producer %s" % producer)
                producer.stop()
        if self.consumers:
            for consumer in self.consumers:
                log.debug("Stopping consumer %s" % consumer)
                consumer.stop()


def setup_logger(verbose):
    global log
    sh = logging.StreamHandler()
    level = verbose and logging.DEBUG or logging.INFO
    log.setLevel(level)
    sh.setLevel(level)
    format = logging.Formatter('[moksha.hub] %(levelname)s %(asctime)s %(message)s')
    sh.setFormatter(format)
    log.addHandler(sh)


def main():
    """ The main MokshaHub method """
    setup_logger('-v' in sys.argv or '--verbose' in sys.argv)
    config_path = get_moksha_config_path()
    if not config_path: 
        print """
            Cannot find Moksha configuration!  Place a development.ini or production.ini
            in /etc/moksha or in the current directory.
        """
        return
    cfg = appconfig('config:' + config_path)
    config.update(cfg)

    hub = CentralMokshaHub()
    global _hub
    _hub = hub

    def handle_signal(signum, stackframe):
        from moksha.hub.reactor import reactor
        if signum in [signal.SIGHUP, signal.SIGINT]:
            hub.stop()
            try:
                reactor.stop()
            except ReactorNotRunning:
                pass

    signal.signal(signal.SIGHUP, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info("Running the MokshaHub reactor")
    reactor.run(installSignalHandlers=False)
    log.info("MokshaHub reactor stopped")


if __name__ == '__main__':
    main()
