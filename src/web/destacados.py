# -*- coding: utf-8 -*-

import os
import re
import config
import itertools
from random import choice

destacado_re = re.compile(r'<h1 id="firstHeading" class="firstHeading">([^<]+).*?'   \
                           '<!-- bodytext -->.*?(?:<table .*?</table>)?\n\s*(<p>.*?)'\
                           '(?:(?:<table id="toc" class="toc">)|(?:<h2)|(?:<div))',
                           re.MULTILINE | re.DOTALL)

class Destacados(object):
    def __init__(self, article_manager, debug=False):
        self.article_manager = article_manager
        self.debug = debug

        with open(config.DESTACADOS) as destacados:
            self.destacados = [x.strip().decode('utf8') for x in destacados]

        self._iter = itertools.cycle(self.destacados)


    def get_destacado(self):
        """Devuelve un destacado al azar... eventualmente."""

        data = None

        while self.destacados and not data:
            if self.debug:
                try:
                    link = self._iter.next()
                except StopIteration:
                    return None
            else:
                link = choice(self.destacados)
            data = self.article_manager.get_item(link)
            if data:
                break

            # destacado roto :|
            print (u"WARNING: Artículo destacado no encontrado: %s" % link).encode("utf-8")
            self.destacados.remove(link)
        else:
            # no hay destacado
            return None

        # La regexp se queda con el título y
        # los párrafos que hay antes de la TOC (si tiene)
        # o antes de la 2da sección
        # Si hay una tabla antes del primer párrafo, la elimina
        # FIXME: Escribir mejor la regex (por lo menos en varias líneas)
        #        o tal vez usar BeautifulSoup
        m = re.search(destacado_re, data)

        if not m:
            print "WARNING: Este articulo rompe la regexp para destacado: %s" % link
            return None
        titulo, primeros_parrafos = m.groups()
        return link, titulo, primeros_parrafos

