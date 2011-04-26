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

"""
:mod:`moksha.widgets.jquery_ui_theme` - jQuery UI Theme
=======================================================

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
"""

# TODO -- can this be replaced with tw2.jqplugins.ui:set_ui_theme_name ?
import tw2.core as twc

ui_theme_css = twc.CSSLink(link='/css/jquery-ui/ui.theme.css', modname=__name__)
ui_base_css = twc.CSSLink(link='/css/jquery-ui/ui.base.css',
                          css=[ui_theme_css],
                          modname=__name__)
