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

# params for building a fallback SVG image
svg_mimetype = 'image/svg+xml'

# include text in SVG only if bigger than this
svg_text_width = 90
svg_text_height = 30

SVG_IMAGE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect x="0%" y="0%" width="100%" height="100%" style="fill:#eee"/>
  <rect x="0%" y="0%" width="100%" height="100%" style="fill:none;stroke:#bbb;stroke-width:4"/>
  <line x1="0%" y1="0%" x2="100%" y2="100%" style="stroke:#bbb;stroke-width:2"/>
  {text}
</svg>"""

SVG_TEXT = """<text x="50%" y="50%" text-anchor="middle"
  dominant-baseline="middle" font-family="sans-serif"
  style="fill:#888">{}</text>"""


class TemplateManager(object):
    """Handle templates from disk."""

    def __init__(self, directory):
        self.directory = directory
        self.cache = {}

    def get_template(self, name):
        if name in self.cache:
            return self.cache[name]

        filename = os.path.join(self.directory, "%s.tpl" % name)
        with codecs.open(filename, "rt", encoding='utf-8') as fh:
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
    orig_link = (config.URL_WIKIPEDIA + "wiki/" + urllib.quote(
                 to3dirs.to_pagina(path).encode('utf-8')).decode('utf-8'))  # py3: don't enc/dec
    return orig_link


def img_fallback(width, height):
    """Build a fallback image to show when original picture is not available."""

    if width > svg_text_width and height > svg_text_height:
        text = SVG_TEXT.format('Sin imagen')  # TODO: _('No image')
    else:
        text = ''
    img = SVG_IMAGE.format(width=width, height=height, text=text)

    return img, svg_mimetype
