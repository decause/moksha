# This file is part of Moksha.
#
# Moksha is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Moksha is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Moksha.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2008, Red Hat, Inc.
# Authors: Luke Macken <lmacken@redhat.com>

from tg import config
from tw.api import Widget, JSLink, js_callback, js_function

orbited_url = 'http://%s:%s' % (config['orbited_host'], config['orbited_port'])
orbited_js = JSLink(link=orbited_url + '/static/Orbited.js')

class OrbitedWidget(Widget):
    params = {
        'onopen': 'A javascript callback for when the connection opens',
        'onread': 'A javascript callback for when new data is read',
        'onclose': 'A javascript callback for when the connection closes',
    }
    onopen = onread = onclose = js_callback('function(){}')
    javascript = [orbited_js]
    template = """
        <script type="text/javascript">
            Orbited.settings.port = %(port)s
            Orbited.settings.hostname = '%(host)s'
            document.domain = document.domain
            TCPSocket = Orbited.TCPSocket
            connect = function() {
                conn = new TCPSocket()
                conn.onread = ${onread}
                conn.onopen = ${onopen}
                conn.onclose = ${onclose}
                conn.open('%(host)s', %(port)s)
            }
            $(document).ready(function() {
                connect()
            })
        </script>
    """ % {'port': config['orbited_port'], 'host': config['orbited_host']}