# -*- coding: utf-8 -*-

# Copyright 2011-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/

import os.path
import re
import string
import urllib.parse

import config
from src.armado import to3dirs

re_header = re.compile(r'\<h1 id="firstHeading" class="firstHeading"\>([^\<]*)\</h1\>')
re_title = re.compile('<title>(.*)</title>')


class TemplateManager(object):
    """Handle templates from disk."""

    def __init__(self, directory):
        self.directory = directory
        self.cache = {}

    def get_template(self, name):
        if name in self.cache:
            return self.cache[name]

        filename = os.path.join(self.directory, "%s.tpl" % name)
        with open(filename, "rt", encoding='utf-8') as fh:
            t = string.Template(fh.read())

        self.cache[name] = t
        return t


def get_title_from_data(data):
    """Extract title from HTML."""
    if data is None:
        return ""
    for regexp in (re_header, re_title):
        match = regexp.search(data)
        if match is not None:
            return match.group(1)
    return ""


def get_orig_link(path):
    """Gets the original external link of a path."""
    orig_link = (config.URL_WIKIPEDIA + "wiki/" + urllib.parse.quote(
                 to3dirs.to_pagina(path)))
    return orig_link
