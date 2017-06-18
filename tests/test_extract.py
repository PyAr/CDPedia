# -*- coding: utf8 -*-

# Copyright 2012-2017 CDPedistas (see AUTHORS.txt)
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
# For further info, check  https://launchpad.net/cdpedia/

"""Tests for the 'extract' module."""

import unittest

from src.imagenes.extract import ImageParser
from src.preproceso import preprocesar


class FakeSearch(object):
    """Simulate a search giving just the image."""
    def __init__(self, url):
        self.url = url

    def groups(self):
        """Fake."""
        return None, self.url, ""


class SearcherTestCase(unittest.TestCase):
    """Tests for the Searcher."""

    def setUp(self):
        """Set up."""
        preprocesar.pages_selector._calculated = True
        self.pi = ImageParser(test=True)
        self.pi.test = False

    def _check(self, url, should_web, should_dsk):
        """Do proper checking."""
        m = FakeSearch(url)
        r = []
        self.pi._reemplaza(r, m)
        dsk, web = r[0]

        self.assertEqual(web, should_web)
        self.assertEqual(dsk, should_dsk)

    def test_replace_wikipedia_commons_5parts(self):
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

    def test_replace_wikipedia_commons_1parts(self):
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

    def test_replace_bits(self):
        url = "//bits.wikimedia.org/skins-1.18/common/images/magnify-clip.png"
        should_web = (
            "http://bits.wikimedia.org/"
            "skins-1.18/common/images/magnify-clip.png"
        )
        should_dsk = "magnify-clip.png"
        self._check(url, should_web, should_dsk)

    def test_replace_timeline(self):
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

    def test_replace_math(self):
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

    def test_replace_math_2(self):
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

    def test_replace_extensions(self):
        url = "/w/extensions/ImageMap/desc-20.png"
        should_web = "https://es.wikipedia.org/w/extensions/ImageMap/desc-20.png"
        should_dsk = "extensions/ImageMap/desc-20.png"
        self._check(url, should_web, should_dsk)

    def test_replace_commons_images(self):
        url = (
            "//upload.wikimedia.org/wikipedia/commons/"
            "thumb/4/40/P_ps.png/35px-P_ps.png"
        )
        should_web = (
            "http://upload.wikimedia.org/wikipedia/commons/"
            "thumb/4/40/P_ps.png/35px-P_ps.png"
        )
        should_dsk = "commons/thumb/4/40/35px-P_ps.png"
        self._check(url, should_web, should_dsk)

    def test_replace_wikimedia_api(self):
        url = "https://wikimedia.org/api/rest_v1/media/math/render/svg/8f85ec5f1c58.svg"
        should_web = url
        should_dsk = "math/render/svg/8f85ec5f1c58.svg"
        self._check(url, should_web, should_dsk)

    def test_extension_fix__path_svg_no_ext(self):
        url = "https://wikimedia.org/api/rest_v1/media/math/render/svg/8f85ec5f1c58"
        should_web = url
        should_dsk = "math/render/svg/8f85ec5f1c58.svg"
        self._check(url, should_web, should_dsk)

    def test_extension_fix__path_svg_ext_ok(self):
        url = "https://wikimedia.org/api/rest_v1/media/math/render/svg/8f85ec5f1c58.svg"
        should_web = url
        should_dsk = "math/render/svg/8f85ec5f1c58.svg"
        self._check(url, should_web, should_dsk)

    def test_extension_fix__path_svg_ext_upper(self):
        url = "https://wikimedia.org/api/rest_v1/media/math/render/svg/8f85ec5f1c58.SVG"
        should_web = url
        should_dsk = "math/render/svg/8f85ec5f1c58.SVG"
        self._check(url, should_web, should_dsk)

    def test_wikipedia_api_graph(self):
        url = '/api/rest_v1/page/graph/png/Londres/0/ad8edccb854188d0e3f0fbf50716096a5bfc2968.png'
        should_web = (
            'https://es.wikipedia.org'
            '/api/rest_v1/page/graph/png/Londres/0/ad8edccb854188d0e3f0fbf50716096a5bfc2968.png'
        )
        should_dsk = 'graph/png/Londres/0/ad8edccb854188d0e3f0fbf50716096a5bfc2968.png'
        self._check(url, should_web, should_dsk)
