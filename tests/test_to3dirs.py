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

"""Tests for the 'to3dirs' module."""

from __future__ import unicode_literals

import unittest

from src.armado import to3dirs


class PageTestCase(unittest.TestCase):

    def test_encoding_nothing(self):
        r = to3dirs.to_filename("moño")
        self.assertEqual(r, "moño")

    def test_encoding_slash(self):
        r = to3dirs.to_filename("foo/bar")
        self.assertEqual(r, "foo%2Fbar")

    def test_encoding_dot(self):
        r = to3dirs.to_filename("foo.bar")
        self.assertEqual(r, "foo%2Ebar")

    def test_encoding_percent(self):
        r = to3dirs.to_filename("foo%bar")
        self.assertEqual(r, "foo%25bar")

    def test_roundtrip_simple(self):
        for word in ("moño", "foo/bar", "foo.bar"):
            r = to3dirs.to_pagina(to3dirs.to_filename(word))
            self.assertEqual(r, word)

    def test_roundtrip_crazy(self):
        word = "foo . bar / baz % more"
        r = to3dirs.to_pagina(to3dirs.to_filename(word))
        self.assertEqual(r, word)


class PathFileTestCase(unittest.TestCase):

    def test_simple(self):
        r = to3dirs.get_path_file("moño")
        self.assertEqual(r, ("m/o/ñ", "moño"))

    def test_short(self):
        r = to3dirs.get_path_file("mo")
        self.assertEqual(r, ("m/o/_", "mo"))

    def test_very_short(self):
        r = to3dirs.get_path_file("m")
        self.assertEqual(r, ("m/_/_", "m"))

    def test_encoding(self):
        r = to3dirs.get_path_file("2.3")
        self.assertEqual(r, ("2/%/2", "2%2E3"))
