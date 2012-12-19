#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2012 CDPedistas (see AUTHORS.txt)
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
# For further info, check  http://code.google.com/p/cdpedia/

"""Tests for the 'extraer' module."""

import unittest

from src.imagenes.extraer import ParseaImagenes


class FakeSearch(object):
    """Simulates a search giving just the image."""
    def __init__(self, url):
        self.url = url

    def groups(self):
        """Fake."""
        return None, self.url, ""


class SearcherTestCase(unittest.TestCase):
    """Tests for the Searcher."""

    def setUp(self):
        """Set up."""
        self.pi = ParseaImagenes(test=True)
        self.pi.test = False

    def _check(self, url, should_web, should_dsk):
        """Do proper checking."""
        m = FakeSearch(url)
        r = []
        self.pi._reemplaza(r, m)
        dsk, web = r[0]

        self.assertEqual(web, should_web)
        self.assertEqual(dsk, should_dsk)

    def test_reemplazar_wikipedia_commons_5parts(self):
        """Reemplazar wikipedia commons with 5 parts."""
        url = (
            "//upload.wikimedia.org/wikipedia/commons/thumb/a/aa/"
            "Coat_of_arms_of_the_Netherlands_-_02.svg/"
            "250px-Coat_of_arms_of_the_Netherlands_-_02.svg.png"
        )
        should_web = (
            "http://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/"
            "Coat_of_arms_of_the_Netherlands_-_02.svg/"
            "250px-Coat_of_arms_of_the_Netherlands_-_02.svg.png"
        )
        should_dsk = (
            "commons/thumb/a/aa/"
            "250px-Coat_of_arms_of_the_Netherlands_-_02.svg.png"
        )
        self._check(url, should_web, should_dsk)

    def test_reemplazar_wikipedia_commons_1parts(self):
        """Reemplazar wikipedia commons with 1 parts."""
        url = (
            "//upload.wikimedia.org/wikipedia/commons/8/88/"
            "Marshall_Islands_coa.jpg"
        )
        should_web = (
            "http://upload.wikimedia.org/wikipedia/commons/8/88/"
            "Marshall_Islands_coa.jpg"
        )
        should_dsk = "commons/8/88/Marshall_Islands_coa.jpg"
        self._check(url, should_web, should_dsk)

    def test_reemplazar_bits(self):
        """Reemplazar bits."""
        url = "//bits.wikimedia.org/skins-1.18/common/images/magnify-clip.png"
        should_web = (
            "http://bits.wikimedia.org/"
            "skins-1.18/common/images/magnify-clip.png"
        )
        should_dsk = "magnify-clip.png"
        self._check(url, should_web, should_dsk)

    def test_reemplazar_timeline(self):
        """Reemplazar timeline."""
        url = (
            "//upload.wikimedia.org/wikipedia/es/"
            "timeline/cc707d3b957628b5e432d7242096abc5.png"
        )
        should_web = (
            "http://upload.wikimedia.org/wikipedia/es/"
            "timeline/cc707d3b957628b5e432d7242096abc5.png"
        )
        should_dsk = "timeline/cc707d3b957628b5e432d7242096abc5.png"
        self._check(url, should_web, should_dsk)

    def test_reemplazar_math(self):
        """Reemplazar math."""
        url = (
            "//upload.wikimedia.org/wikipedia/es/"
            "math/6/7/e/67ed4566dba0caae24ec4cf25133f200.png"
        )
        should_web = (
            "http://upload.wikimedia.org/wikipedia/es/"
            "math/6/7/e/67ed4566dba0caae24ec4cf25133f200.png"
        )
        should_dsk = "math/6/7/e/67ed4566dba0caae24ec4cf25133f200.png"
        self._check(url, should_web, should_dsk)

    def test_reemplazar_math_2(self):
        """Reemplazar math, 2."""
        url = (
            '//upload.wikimedia.org/'
            'math/9/6/3/963fb8b00ffd99f327c476f0865a9cfe.png'
        )
        should_web = (
            'http://upload.wikimedia.org/'
            'math/9/6/3/963fb8b00ffd99f327c476f0865a9cfe.png'
        )
        should_dsk = 'math/9/6/3/963fb8b00ffd99f327c476f0865a9cfe.png'
        self._check(url, should_web, should_dsk)

    def test_reemplazar_extensions(self):
        """Reemplazar the extensions subdir."""
        url = "/w/extensions/ImageMap/desc-20.png"
        should_web = (
            "http://es.wikipedia.org/w/extensions/ImageMap/desc-20.png"
        )
        should_dsk = "extensions/ImageMap/desc-20.png"
        self._check(url, should_web, should_dsk)
