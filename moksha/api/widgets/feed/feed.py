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

import moksha
import moksha.utils
import logging

from tw.api import Widget
from shove import Shove
from feedcache.cache import Cache

log = logging.getLogger(__name__)

# An in-memory sqlite feed cache.  Utilized when the moksha WSGI middleware
# is unavailable.  By default, it will try and use the centralized
# moksha.utils.feed_cache, which is setup by the middleware, but will gracefully
# fallback to this cache.
feed_storage = None
feed_cache = None

class Feed(Widget):
    """
    The Moksha Feed object.

    A Feed is initialized with an id and a url, and automatically handles the
    fetching, parsing, and caching of the data.

    """
    url = None
    template = 'mako:moksha.api.widgets.feed.templates.feed_home'
    params = {
            'title': 'The title of this feed',
            'link': 'The url to the site that this feed is for',
            'entries': 'A list of feed entries',
    }

    def __new__(cls, *args, **kw):
        """ If we're instantiated with a specific view, then use the 
        appropriate template 
        Available views: home, canvas, profile

        :deprecated: This is old, and will be going away soon
        """
        view = kw.get('view', False)
        if not view:
            view = getattr(cls, 'view', False)
        if view:
            class AlternateFeedView(cls):
                template = 'mako:moksha.feed.templates.feed_%s' % view
            return super(Feed, cls).__new__(AlternateFeedView, *args, **kw)
        return super(Feed, cls).__new__(cls, *args, **kw)

    def iterentries(self, d=None, limit=None):
        url = self.url or d.get('url')
        id = d and d.get('id', self.id) or self.id
        if moksha.utils.feed_cache:
            feed = moksha.utils.feed_cache.fetch(url)
        else:
            # MokshaMiddleware not running, so setup our own feed cache.
            # This allows us to use this object outside of WSGI requests.
            global feed_cache, feed_storage
            if not feed_cache:
                feed_storage = Shove('sqlite:///feeds.db', compress=True)
                feed_cache = Cache(feed_storage)
            feed = feed_cache.fetch(url)
        if not (200 <= feed.get('status', 200) < 400):
            log.warning('Got %s status from %s: %s' % (
                        feed['status'], url, feed.headers.get('status')))
            if d:
                d['title'] = feed.headers.get('status')
                d['link'] = feed.feed.get('link')
            return
        if d:
            d['link'] = feed.feed.get('link')
            try:
                d['title'] = feed.feed.title
            except AttributeError:
                d['title'] = 'Unable to parse feed'
                return
        for i, entry in enumerate(feed.get('entries', [])):
            entry['uid'] = '%s_%d' % (id, i)
            entry['link'] = entry.get('link')
            if i == limit:
                break
            yield entry

    def get_entries(self, url=None):
        d = {}
        if url:
            d['url'] = url
        return [entry for entry in self.iterentries(d=d)]

    def num_entries(self):
        return len(self.get_entries())

    def update_params(self, d):
        super(Feed, self).update_params(d)
        d['entries'] = []
        limit = d.get('limit')
        for entry in self.iterentries(d, limit=limit):
            d['entries'].append(entry)

    def close(self):
        global feed_storage
        try:
            feed_storage.close()
        except:
            pass
