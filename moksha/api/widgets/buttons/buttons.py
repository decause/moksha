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
:mod:`moksha.api.widgets.buttons` - Fancy Button CSS
====================================================

This module contains a ToscaWidget for the mbButtons
project::

    http://www.open-lab.com/mb.ideas/index.html#mbButtons

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
"""

import tw2.core as twc

buttons_css = twc.CSSLink(filename='static/buttons.css',
                          media='all', modname=__name__)
buttons_dir = twc.DirLink(filename='static/images',
                          modname=__name__)
static_images = twc.Link(filename='static/images/ventitre.gif',
                         modname=__name__)
