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

import re
import urllib
import os.path
import string

from src.armado import to3dirs
import config

re_header = re.compile('\<h1 id="firstHeading" class="firstHeading"\>([^\<]*)\</h1\>')
re_title = re.compile('<title>(.*)</title>')

class TemplateManager(object):
    '''Maneja los templates en disco.'''

    def __init__(self, directorio):
        self.directorio = directorio
        self.cache = {}

    def get_template(self, nombre):
        if nombre in self.cache:
            return self.cache[nombre]

        nomarch = os.path.join(self.directorio, "%s.tpl" % nombre)
        with open(nomarch, "rb") as f:
            t = string.Template(f.read())

        self.cache[nombre] = t
        return t

def get_title_from_data(data):
    if data is None:
        return u""
    for regexp in (re_header, re_title):
        match = regexp.search(data)
        if match is not None:
            return match.group(1)
    return u""


def get_orig_link(path):
    """Gets the original external link of a path."""
    orig_link = config.URL_WIKIPEDIA + u"wiki/" + \
                urllib.quote(to3dirs.to_pagina(path).encode("utf-8"))
    return orig_link
