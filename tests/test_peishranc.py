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

import unittest

from src.preproceso.preprocesadores import Peishranc, SCORE_PEISHRANC


class FakeWikiArchivo(object):
    """Fake Wikiarchivo, just to hold the html."""
    def __init__(self, html, url='url'):
        self.html = html
        self.url = url


class PeishrancTests(unittest.TestCase):
    """Tests para el Peishranc."""

    def setUp(self):
        """Set up."""
        self.peishranc = Peishranc()

    def test_cero_a_la_pagina(self):
        """Link simple."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foobar">FooBar</a> dcba')
        v, _ = self.peishranc(fwa)
        self.assertEqual(v, 0)

    def test_simple(self):
        """Link simple."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foobar">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', SCORE_PEISHRANC)])

    def test_con_clase(self):
        """Link que tiene 'class'."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar" class="clase">FooBar</a> dcba'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', SCORE_PEISHRANC)])

    def test_hasta_el_numeral(self):
        """El link es hasta el numeral."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foobar#xy">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', SCORE_PEISHRANC)])

    def test_doble_distinto(self):
        """Dos links diferentes."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
            'mmm kkk lll <a href="/wiki/otrapag">Otra pag</a> final\n'
        )
        _, r = self.peishranc(fwa)
        should = [
            (u'foobar', SCORE_PEISHRANC),
            (u'otrapag', SCORE_PEISHRANC),
        ]
        self.assertEqual(r, should)

    def test_doble_igual(self):
        """Dos links iguales."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
            'mmm kkk lll <a href="/wiki/foobar">Lo mismo</a> final\n'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 2 * SCORE_PEISHRANC)])

    def test_autobombo(self):
        """No dar puntaje a la misma pag."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
            'mmm kkk lll <a href="/wiki/urlanalizada">Lo mismo</a> final\n',
            url='urlanalizada')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', SCORE_PEISHRANC)])

    def test_class_image(self):
        """Descartamos los class image."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar" class="image">FooBar</a> dcba'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [])

    def test_class_internal(self):
        """Descartamos los class internal."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar" class="internal">FooBar</a> dcba'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [])

    def test_doble_con_class(self):
        """Dos links diferentes, uno con class ok el otro no."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar" class="image">FooBar</a> dcbrr ppp\n'
            'mmm kkk lll <a href="/wiki/otrapag" class="ok">Otra pag</a> fin\n'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'otrapag', SCORE_PEISHRANC)])

    def test_barra(self):
        """Reemplazamos la /."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foo/bar">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'fooSLASHbar', SCORE_PEISHRANC)])

    def test_unquote(self):
        """Aplicamos unquote al link."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/f%C3%B3u">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'fóu', SCORE_PEISHRANC)])
