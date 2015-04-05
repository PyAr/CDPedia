# -*- coding: utf-8 -*-
import os
import unittest

from src.armado.to3dirs import NULL, BARRA, to_path, from_path, to_filename, to_pagina

def _to_complete_path(pagina):
    return '/'.join((to_path(pagina), to_filename(pagina)))


class To3DirsTestCase(unittest.TestCase):

    def test_to_path(self):
        test_paths = (
          ((u"*", NULL, NULL), u"*/"),
          ((u"a", u"b", u"c"), u"abcdefgh"),
          ((u"á", NULL, NULL), u"á"),
          ((u"á", u"þ", NULL), u"áþ"),
          ((u"$", u"9", NULL), u"$9.99"),
          ((u"a", u"b", u"c"), u"Anexo:abcdefgh"),
          ((u'a',u':',u'b'), u'Anexo:a:blanco'),
          ((u'N',u'o',u'e'), u'Noestoy:Anexo:a:blanco'),
        )

        for path, orig in test_paths:
            self.assertEqual(os.path.join(*path), to_path(orig))

    def test_to_filename(self):
        test_paths = (
          (u"*" + BARRA, u"*/"),
          (u"Anexo:*" + BARRA, u"Anexo:*/"),
          (BARRA + BARRA + u':Tr3s.Jeans', u'//:Tr3s.Jeans'),
        )

        for path, orig in test_paths:
            self.assertEqual(path, to_filename(orig))

    def test_to_pagina(self):
        test_paths = (
            u"*/",
            u"Anexo:*/",
            u'//:Tr3s.Jeans',
        )

        for s in test_paths:
            self.assertEqual(to_pagina(to_filename(s)), s)

    def test_from_path(self):
        self.assertEqual(from_path(_to_complete_path(u"unnombre")) , u"unnombre")
        self.assertEqual(from_path(_to_complete_path(u"/s")) , u"/s")
        self.assertEqual(from_path(_to_complete_path(u"s/s/s/")) , u"s/s/s/")
        self.assertEqual(from_path(_to_complete_path(u"s/s/s/SLASH")) , u"s/s/s//")

if __name__ == '__main__':
    unittest.main()
