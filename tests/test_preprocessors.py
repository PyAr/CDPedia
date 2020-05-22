#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2017-2020 CDPedistas (see AUTHORS.txt)
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

"""Tests for the src.preprocessing.preprocessors module."""

from __future__ import unicode_literals

import os

import bs4

from src.preprocessing.preprocessors import HTMLCleaner
from .utils import load_test_article, FakeWikiFile

import pytest


@pytest.fixture
def article_1():
    return load_test_article('article_with_inlinemath')


@pytest.fixture
def article_2():
    return load_test_article('article_with_images')


class TestHTMLCleaner(object):
    """Tests for HTMLCleaner preprocessor."""

    @pytest.fixture
    def cleaner(self):
        return HTMLCleaner()

    def test_remove_inlinemath(self, cleaner, article_1):
        html, wikifile = article_1
        text = 'MJX-TeXAtom-ORD'
        assert text in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text not in wikifile.html

    def test_remove_img_srcset(self, cleaner, article_2):
        html, wikifile = article_2
        text = 'srcset="//upload.wikimedia.org/'
        assert text in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text not in wikifile.html

    def test_remove_not_last_version_text(self, cleaner):
        html = ('<div><div id="contentSub">\n<div class="mw-revision warningbox">'
                'spam spam spam\n</div> </div>foo bar</div>')
        html_fixed = '<div><div id="contentSub"></div>foo bar</div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_edit_section(self, cleaner):
        html = ('<h2>Title<span class="mw-editsection">'
                '<span>[Edit]</span></span></h2>')
        html_fixed = '<h2>Title<span class="mw-editsection"></span></h2>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_ambox(self, cleaner):
        html = ('<table class="ambox ambox-content">'
                '<tr><td>Spam Spam</td></tr></table>')
        html_fixed = '<table class="ambox ambox-content"></table>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_links_keep_text(self, cleaner, article_2):
        html, wikifile = article_2
        texts_keep = ('Discusión', 'Categoría')
        texts_remove = tuple(t[0] for t in HTMLCleaner.unwrap_links)
        assert all(text in html for text in texts_keep)
        assert all(text in html for text in texts_remove)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert all(text in wikifile.html for text in texts_keep)
        assert not all(text in wikifile.html for text in texts_remove)

    def test_remove_hidden_subtitle(self, cleaner):
        html = '<div><div id="siteSub">Spam Spam</div>foo bar</div>'
        html_fixed = '<div>foo bar</div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_jump_links(self, cleaner, article_2):
        html, wikifile = article_2
        text1 = '<a class="mw-jump-link" href="#mw-head">'
        text2 = '<a class="mw-jump-link" href="#p-search">'
        assert text1 in html
        assert text2 in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text1 not in wikifile.html
        assert text2 not in wikifile.html

    def test_remove_inline_alerts(self, cleaner):
        # Make shure references like `[1]` are not touched.
        html = ('<p>Foo<sup>[<i><a href="link">spam spam<a></i>]</sup> '
                'bar<sup>[<a href="#cite_note-1">1</a>]</sup></p>')
        html_fixed = '<p>Foo bar<sup>[<a href="#cite_note-1">1</a>]</sup></p>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_printfooter(self, cleaner, article_2):
        html, wikifile = article_2
        text = '<div class="printfooter">'
        assert text in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text not in wikifile.html

    def test_remove_hidden_categories(self, cleaner):
        html = ('<div id="catlinks"><div id="mw-normal-catlinks">Foo</div>'
                '<div id="mw-hidden-catlinks">Spam</div></div>')
        html_fixed = '<div id="catlinks"><div id="mw-normal-catlinks">Foo</div></div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_comments(self, cleaner):
        html = ('<div>foo<!--spam spam--></div>'
                '<div>bar</div><!--\nspam\nspam\nspam\n-->')
        html_fixed = '<div>foo</div><div>bar</div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

    def test_remove_parsing_errors(self, cleaner):
        html = ('<p>Foo<span class="error mw-ext-cite-error" lang="es">'
               'Spam Spam</span> bar</p>')
        html_fixed = '<p>Foo bar</p>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.html

