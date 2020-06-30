# -*- coding: utf8 -*-

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

"""Tests for Peishranc preprocessor."""

from __future__ import unicode_literals

import bs4

from src.preprocessing.preprocessors import Peishranc, SCORE_PEISHRANC
from .utils import FakeWikiFile

import pytest


@pytest.fixture
def peishranc():
    """Set PeishRanc instance to use in all tests."""
    return Peishranc()


def test_zero_page_score(peishranc):
    """Test a simple link."""
    wikifile = FakeWikiFile('abcd <a href="/wiki/foobar">FooBar</a> dcba')
    v, _ = peishranc(wikifile)
    assert v == 0


def test_simple_link(peishranc):
    """Test a simple link."""
    wikifile = FakeWikiFile('abcd <a href="/wiki/foobar">FooBar</a> dcba')
    _, r = peishranc(wikifile)
    assert r == [('foobar', SCORE_PEISHRANC)]


def test_link_with_class(peishranc):
    """Test link with `class` attribute."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar" class="clase">FooBar</a> dcba'
    )
    _, r = peishranc(wikifile)
    assert r == [('foobar', SCORE_PEISHRANC)]


def test_remove_link_prefix_fragment(peishranc):
    """Link is text between prefix and numeral."""
    wikifile = FakeWikiFile('abcd <a href="/wiki/foobar#xy">FooBar</a> dcba')
    _, r = peishranc(wikifile)
    assert r == [('foobar', SCORE_PEISHRANC)]


def test_two_different_links(peishranc):
    """Test score given to two different links."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
        'mmm kkk lll <a href="/wiki/otrapag">Otra pag</a> final\n'
    )
    _, r = peishranc(wikifile)
    # sort the results by link name
    r = sorted(r, key=lambda res: res[0])
    should = [
        ('foobar', SCORE_PEISHRANC),
        ('otrapag', SCORE_PEISHRANC),
    ]
    assert r == should


def test_two_equal_links(peishranc):
    """Test score given to two equal links."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
        'mmm kkk lll <a href="/wiki/foobar">Lo mismo</a> final\n'
    )
    _, r = peishranc(wikifile)
    assert r == [('foobar', 2 * SCORE_PEISHRANC)]


def test_self_praise(peishranc):
    """Do not score links to the page that's being processed."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
        'mmm kkk lll <a href="/wiki/urlanalizada">Lo mismo</a> final\n',
        url='urlanalizada')
    _, r = peishranc(wikifile)
    assert r == [('foobar', SCORE_PEISHRANC)]


def test_discard_image_class(peishranc):
    """Discard links of `image` class."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar" class="image">FooBar</a> dcba'
    )
    _, r = peishranc(wikifile)
    assert r == []


def test_discard_internal_class(peishranc):
    """Discard links of `internal` class."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar" class="internal">FooBar</a> dcba'
    )
    _, r = peishranc(wikifile)
    assert r == []


def test_two_links_with_class(peishranc):
    """Test one link with good class and other with bad class."""
    wikifile = FakeWikiFile(
        'abcd <a href="/wiki/foobar" class="image">FooBar</a> dcbrr ppp\n'
        'mmm kkk lll <a href="/wiki/otrapag" class="ok">Otra pag</a> fin\n'
    )
    _, r = peishranc(wikifile)
    assert r == [('otrapag', SCORE_PEISHRANC)]


def test_replace_slash(peishranc):
    """Test replacement of `/` with `SLASH` in final link text."""
    wikifile = FakeWikiFile('abcd <a href="/wiki/foo/bar">FooBar</a> dcba')
    _, r = peishranc(wikifile)
    assert r == [('fooSLASHbar', SCORE_PEISHRANC)]


def test_unquote(peishranc):
    """Test link unquoting."""
    wikifile = FakeWikiFile('abcd <a href="/wiki/f%C3%B3u">FooBar</a> dcba')
    _, r = peishranc(wikifile)
    assert r == [('fóu', SCORE_PEISHRANC)]


def test_no_link(peishranc):
    """Test no link in page."""
    wikifile = FakeWikiFile('abcd <p>foo bar baz</p> dcba')
    v, r = peishranc(wikifile)
    assert v == 0
    assert r == []

