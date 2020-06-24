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

from __future__ import unicode_literals

import codecs
import os.path
import re
import string
import urllib

import config
from src.armado import to3dirs


re_header = re.compile(r'\<h1 id="firstHeading" class="firstHeading"\>([^\<]*)\</h1\>')
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
        with codecs.open(nomarch, "rt", encoding='utf-8') as fh:
            t = string.Template(fh.read())

        self.cache[nombre] = t
        return t


def get_title_from_data(data):
    if data is None:
        return ""
    for regexp in (re_header, re_title):
        match = regexp.search(data)
        if match is not None:
            return match.group(1)
    return ""


def get_orig_link(path):
    """Gets the original external link of a path."""
    orig_link = (config.URL_WIKIPEDIA + "wiki/" + urllib.quote(
                 to3dirs.to_pagina(path).encode('utf-8')).decode('utf-8'))  # py3: don't enc/dec
    return orig_link


def img_fallback(width, height):
    """Build a fallback image to show when original picture is not available."""

    # minimum dimensions to include text
    min_width, min_height = 90, 30
    mimetype = 'image/svg+xml'

    svg = """<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
          <rect x="0%" y="0%" width="100%" height="100%" style="fill:#eee"/>
          <rect x="0%" y="0%" width="100%" height="100%"
                style="fill:none;stroke:#bbb;stroke-width:4"/>
          <line x1="0%" y1="0%" x2="100%" y2="100%"
                style="stroke:#bbb;stroke-width:2"/>
          {text}
        </svg>"""

    txt = """<text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle"
                   font-family="sans-serif" style="fill:#888">{}</text>"""

    if width > min_width and height > min_height:
        text = txt.format('Sin imágen')  # TODO: _('No image')
    else:
        text = ''
    img = svg.format(width=width, height=height, text=text)
    return img, mimetype
