# -*- coding: utf8 -*-

import unittest

from src.preproceso.preprocesadores import Peishranc

class FakeWikiArchivo(object):
    """Fake Wikiarchivo, just to hold the html."""
    def __init__(self, html, url='url'):
        self.html = html
        self.url = url

class PeishrancTests(unittest.TestCase):
    """Tests para el Peishranc."""

    def setUp(self):
        """Set up."""
        self.peishranc = Peishranc(None)

    def test_cero_a_la_pagina(self):
        """Link simple."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foobar">FooBar</a> dcba')
        v, _ = self.peishranc(fwa)
        self.assertEqual(v, 0)

    def test_simple(self):
        """Link simple."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foobar">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 1)])

    def test_con_clase(self):
        """Link que tiene 'class'."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar" class="clase">FooBar</a> dcba'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 1)])

    def test_hasta_el_numeral(self):
        """El link es hasta el numeral."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foobar#xy">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 1)])

    def test_doble_distinto(self):
        """Dos links diferentes."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
            'mmm kkk lll <a href="/wiki/otrapag">Otra pag</a> final\n'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 1), (u'otrapag', 1)])

    def test_doble_igual(self):
        """Dos links iguales."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
            'mmm kkk lll <a href="/wiki/foobar">Lo mismo</a> final\n'
        )
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 2)])

    def test_autobombo(self):
        """No dar puntaje a la misma pag."""
        fwa = FakeWikiArchivo(
            'abcd <a href="/wiki/foobar">FooBar</a> dcba qwerty rrr ppp\n'
            'mmm kkk lll <a href="/wiki/urlanalizada">Lo mismo</a> final\n',
            url='urlanalizada')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'foobar', 1)])

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
        self.assertEqual(r, [(u'otrapag', 1)])

    def test_comienza_archivo(self):
        """Descartamos los que comienzan con Archivo."""
        fwa = FakeWikiArchivo('ab <a href="/wiki/Archivo:foobar">Foo</a> dc')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [])

    def test_barra(self):
        """Reemplazamos la /."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/foo/bar">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'fooSLASHbar', 1)])

    def test_unquote(self):
        """Aplicamos unquote al link."""
        fwa = FakeWikiArchivo('abcd <a href="/wiki/f%C3%B3u">FooBar</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'fóu', 1)])

    def test_namespace_incluido_simple(self):
        """El link es parte de un namespace que incluímos."""
        fwa = FakeWikiArchivo('ad <a href="/wiki/Anexo:foobar">FooBar</a> dcb')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'Anexo:foobar', 1)])

    def test_namespace_incluido_acento(self):
        """El link es parte de un namespace ok, pero con nombre acentuado."""
        fwa = FakeWikiArchivo('a <a href="/wiki/Categoría:foobar">Foo</a> a')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [(u'Categoría:foobar', 1)])

    def test_namespace_excluido(self):
        """El link es parte de un namespace que NO incluímos."""
        fwa = FakeWikiArchivo('abd <a href="/wiki/Imagen:foobar">Foo</a> dcba')
        _, r = self.peishranc(fwa)
        self.assertEqual(r, [])

if __name__ == "__main__":
    unittest.main()
