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

import logging

from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from twisted.internet.task import LoopingCall

from moksha.hub.hub import MokshaHub
from moksha.lib.helpers import create_app_engine

log = logging.getLogger('moksha.hub')

class DataStream(object):
    """ The parent DataStream class. """

    def __init__(self):
        self.hub = MokshaHub()
        self.log = log

        # If the stream specifies an 'app', then setup `self.engine` to
        # be a SQLAlchemy engine for that app, along with a configured DBSession
        app = getattr(self, 'app', None)
        self.engine = self.DBSession = None
        if app:
            self.engine = create_app_engine(app)
            self.DBSession = sessionmaker(bind=self.engine)()

    def send_message(self, topic, message):
        try:
            self.hub.send_message(topic, message)
        except Exception, e:
            log.error('Cannot send message: %s' % e)

    def stop(self):
        if hasattr(self, 'hub') and self.hub:
            self.hub.close()
        if hasattr(self, 'DBSession') and self.DBSession:
            self.DBSession.close()


class PollingDataStream(DataStream):
    """ A self-polling data stream.

    This class represents a data stream that wakes up at a given frequency,
    and calls the :meth:`poll` method.
    """
    frequency = None # Either a timedelta object, or the number of seconds
    now = False

    def __init__(self):
        super(PollingDataStream, self).__init__()
        self.timer = LoopingCall(self.poll)
        if isinstance(self.frequency, timedelta):
            seconds = self.frequency.seconds + \
                    (self.frequency.days * 24 * 60 * 60) + \
                    (self.frequency.microseconds / 1000000.0)
        else:
            seconds = self.frequency
        log.debug("Setting a %s second timer" % seconds)
        self.timer.start(seconds, now=self.now)

    def poll(self):
        raise NotImplementedError

    def stop(self):
        super(PollingDataStream, self).stop()
        try:
            if hasattr(self, 'timer'):
                self.timer.stop()
        except Exception, e:
            self.log.warn(e)
