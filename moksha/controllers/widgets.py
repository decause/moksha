# This file is part of Moksha.
# Copyright (C) 2008-2009  Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors: Luke Macken <lmacken@redhat.com>

import moksha
import logging

from tg import expose, tmpl_context, flash, redirect

from moksha.exc import WidgetNotFound
from moksha.lib.base import Controller
from moksha.widgets.source import code_widget
from moksha.widgets.container import container
from moksha.api.widgets.stomp import stomp_widget

log = logging.getLogger(__name__)

class WidgetController(Controller):

    @expose('mako:moksha.templates.widget')
    def default(self, widget, chrome=None, live=False, **kw):
        """ Display a single widget.

        :chrome: Display in a Moksha Container
        :live: Inject a socket for live widgets
        """
        options = {}
        options.update(kw)
        w = moksha._widgets.get(widget)
        if not w:
            raise WidgetNotFound(widget)
        if chrome and getattr(w['widget'], 'visible', True):
            tmpl_context.widget = container
            options['content'] = w['widget']
            options['title'] =  w['name']
            options['id'] = widget + '_container'

            # Allow widgets to specify container options
            container_options = getattr(w['widget'], 'container_options', None)
            if container_options:
                options.update(container_options)
        else:
            tmpl_context.widget = w['widget']
        if live:
            tmpl_context.moksha_socket = stomp_widget
        return dict(options=options)

    @expose('mako:moksha.templates.widget')
    def source(self, widget):
        """ Display the source code for a given widget """
        tmpl_context.widget = code_widget
        widget = None
        try:
            widget = moksha.get_widget(widget)
        except:
            msg = "Widget %s not found" % widget
            flash(msg)
            log.debug(msg)
            redirect('/')
        return dict(options={'widget': widget})
