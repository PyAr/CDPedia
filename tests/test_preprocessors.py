#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2017 CDPedistas (see AUTHORS.txt)
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

"""Tests for the src.preprocessing.preprocessors module."""

import os
import unittest

from src.preprocessing.preprocessors import HTMLCleaner
from .utils import load_fixture, FakeWikiFile


class HTMLCleanerTestCase(unittest.TestCase):
    """Tests for HTMLCleaner."""

    def setUp(self):
        """Prepare test fixtures."""
        self.process = HTMLCleaner()
        self.article_1 = load_fixture('article_with_images.html')
        self.article_2 = load_fixture('article_with_inlinemath.html')

    def test_remove_inlinemath(self):
        assert 'MJX-TeXAtom-ORD' in self.article_2
        wikifile = FakeWikiFile(self.article_2)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertNotIn('MJX-TeXAtom-ORD', wikifile.html)

    def test_remove_img_srcset(self):
        text = 'srcset="//upload.wikimedia.org/'
        assert text in self.article_1
        wikifile = FakeWikiFile(self.article_1)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertNotIn(text, wikifile.html)

    def test_remove_not_last_version_text(self):
        html = ('<div><div id="contentSub">\n<div class="mw-revision warningbox">'
                'spam spam spam\n</div> </div>foo bar</div>')
        html_fixed = '<div><div id="contentSub"></div>foo bar</div>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_edit_section(self):
        html = ('<h2>Title<span class="mw-editsection">'
                '<span>[Edit]</span></span></h2>')
        html_fixed = '<h2>Title<span class="mw-editsection"></span></h2>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_ambox(self):
        html = ('<table class="ambox ambox-content">'
                '<tr><td>Spam Spam</td></tr></table>')
        html_fixed = '<table class="ambox ambox-content"></table>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_links_keep_text(self):
        texts_keep = ('Discusión', 'Categoría')
        texts_remove = tuple(t[0] for t in HTMLCleaner.unwrap_links)
        assert all(text in self.article_1 for text in texts_keep)
        assert all(text in self.article_1 for text in texts_remove)
        wikifile = FakeWikiFile(self.article_1)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        assert all(text in wikifile.html for text in texts_keep)
        assert not all(text in wikifile.html for text in texts_remove)

    def test_remove_hidden_subtitle(self):
        html = '<div><div id="siteSub">Spam Spam</div>foo bar</div>'
        html_fixed = '<div>foo bar</div>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_jump_links(self):
        text1 = '<a class="mw-jump-link" href="#mw-head">'
        text2 = '<a class="mw-jump-link" href="#p-search">'
        assert text1 in self.article_1
        assert text2 in self.article_1
        wikifile = FakeWikiFile(self.article_1)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        assert text1 not in wikifile.html
        assert text2 not in wikifile.html

    def test_remove_inline_alerts(self):
        # Make shure references like `[1]` are not touched.
        html = ('<p>Foo<sup>[<i><a href="link">spam spam<a></i>]</sup> '
                'bar<sup>[<a href="#cite_note-1">1</a>]</sup></p>')
        html_fixed = '<p>Foo bar<sup>[<a href="#cite_note-1">1</a>]</sup></p>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_printfooter(self):
        text = '<div class="printfooter">'
        assert text in self.article_1
        wikifile = FakeWikiFile(self.article_1)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        assert text not in wikifile.html

    def test_remove_hidden_categories(self):
        html = ('<div id="catlinks"><div id="mw-normal-catlinks">Foo</div>'
                '<div id="mw-hidden-catlinks">Spam</div></div>')
        html_fixed = '<div id="catlinks"><div id="mw-normal-catlinks">Foo</div></div>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_comments(self):
        html = ('<div>foo<!--spam spam--></div>'
                '<div>bar</div><!--\nspam\nspam\nspam\n-->')
        html_fixed = '<div>foo</div><div>bar</div>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

    def test_remove_parsing_errors(self):
        html = ('<p>Foo<span class="error mw-ext-cite-error" lang="es">'
               'Spam Spam</span> bar</p>')
        html_fixed = '<p>Foo bar</p>'
        wikifile = FakeWikiFile(html)
        result = self.process(wikifile)
        self.assertEqual(result, (0, []))
        self.assertEqual(html_fixed, wikifile.html)

