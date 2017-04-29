#!/usr/bin/env python

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

"""Tests for the src.preproceso.preprocesadores module."""

import unittest
import os

from src.preproceso.preprocesadores import HTMLCleaner


class FakeWikiFile:
    def __init__(self, html):
        self.html = html


def _load_fixture(filename):
    """Load a fixture from disk."""
    filepath = os.path.join(os.getcwd(), 'tests', 'fixtures', filename)
    with open(filepath, "rb") as fh:
        return fh.read()


class HTMLCleanerTestCase(unittest.TestCase):
    """Tests for HTMLCleaner."""

    def test_remove_inlinemath(self):
        html = _load_fixture('article_with_inlinemath.html')
        assert 'MJX-TeXAtom-ORD' in html
        pp = HTMLCleaner()
        wf = FakeWikiFile(html)
        result = pp(wf)
        self.assertEqual(result, (0, []))
        self.assertNotIn('MJX-TeXAtom-ORD', wf.html)
