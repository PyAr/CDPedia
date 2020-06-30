# -*- coding: utf8 -*-

# Copyright 2012-2020 CDPedistas (see AUTHORS.txt)
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

"""Tests for the 'extract' module."""

import unittest

import bs4

from src.images.extract import ImageParser
from .utils import load_fixture


class ReplaceImageParserTestCase(unittest.TestCase):
    """Tests for the ImageParser."""

    def setUp(self):
        """Set up."""
        self.soup = bs4.BeautifulSoup(features="lxml")

    def _check(self, url, should_web, should_dsk):
        """Do proper checking."""

        tag = self.soup.new_tag("img", src=url)

        dsk, web = ImageParser.replace(tag)

        self.assertEqual(web, should_web)
        self.assertEqual(dsk, should_dsk)
        self.assertEqual(tag.attrs["src"], '/images/' + should_dsk)

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


def test_append_size_querystring():
    soup = bs4.BeautifulSoup(features="html.parser")
    url = ("//upload.wikimedia.org/wikipedia/commons/"
           "thumb/4/40/P_ps.png/35px-P_ps.png")

    tag = soup.new_tag("img", src=url, width='100px', height='50px')

    ImageParser.replace(tag)

    assert tag.attrs.get("width") is None
    assert tag.attrs.get("height") is None
    assert tag.attrs['src'].endswith("?s=100px-50px")


def test_no_size_querystring_when_size_undefined():
    soup = bs4.BeautifulSoup(features="html.parser")
    url = ("//upload.wikimedia.org/wikipedia/commons/"
           "thumb/4/40/P_ps.png/35px-P_ps.png")

    tag = soup.new_tag("img", src=url)

    ImageParser.replace(tag)

    assert tag.attrs['src'].endswith(".png")


def test_parse_html():
    html = load_fixture('article_with_inlinemath.html')
    base_soup = bs4.BeautifulSoup(html, features="html.parser")

    html, _ = ImageParser.parse_html(html, chosen_pages=set())

    soup = bs4.BeautifulSoup(html, features="html.parser")

    assert len(soup.find_all("img")) == 7
    assert len(soup.find_all("a")) == 221
    assert len(soup.find_all("a", "external")) == 8

    # no link starting with //
    assert any([tag.attrs['href'].startswith("//") for tag in soup.find_all("a")])

    assert "data-file-width" not in html
    assert "data-file-height" not in html

    # check that the "image links" are removed
    assert len(base_soup.find_all("a", "image")) != 0
    assert len(soup.find_all("a", "image")) == 0

    # check that the only image removed is "Special:CentralAutoLogin"
    assert len(soup.find_all("img")) == len(base_soup.find_all("img")) - 1
    assert any(["AutoLogin" in tag.attrs["src"] for tag in base_soup.find_all("img")])
    assert not any(["AutoLogin" in tag.attrs["src"] for tag in soup.find_all("img")])


def test_parse_html_remove_selflinks():
    link_without_href = '<a class="mw-selflink selflink">Argentina</a>'

    html, _ = ImageParser.parse_html(link_without_href, chosen_pages=set())

    # check that links without href are removed
    soup = bs4.BeautifulSoup(html, "lxml")
    assert len(soup.find_all("a", href=None)) == 0
    assert 'Argentina' in html


def test_included_pages_links():
    original_html = load_fixture('article_with_inlinemath.html')

    html, _ = ImageParser.parse_html(original_html, chosen_pages=set())
    soup1 = bs4.BeautifulSoup(html, "lxml")

    html, _ = ImageParser.parse_html(original_html, chosen_pages={"Wikcionario"})
    soup2 = bs4.BeautifulSoup(html, "lxml")

    no_chosen_pages_count = len(soup1.find_all("a", "nopo"))
    assert no_chosen_pages_count - 1 == len(soup2.find_all("a", "nopo"))
