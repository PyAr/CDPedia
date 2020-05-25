# -*- coding: utf-8 -*-

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

import config
import itertools
import re
from random import choice

destacado_re = re.compile(r'<h1 id="firstHeading" class="firstHeading">([^<]+).*?'
                          r'<!-- bodytext -->.*?(?:<table .*?</table>)?\n\s*(<p>.*?)'
                          r'(?:(?:<table id="toc" class="toc">)|(?:<h2)|(?:<div))',
                          re.MULTILINE | re.DOTALL)


class Destacados(object):
    def __init__(self, article_manager, debug=False, verbose=False):
        self.article_manager = article_manager
        self.debug = debug
        self.verbose = verbose

        with open(config.DESTACADOS) as destacados:
            self.destacados = [x.strip() for x in destacados]

        self._iter = itertools.cycle(self.destacados)

    def get_destacado(self):
        """Devuelve un destacado al azar... eventualmente."""

        data = None

        while self.destacados and not data:
            if self.debug:
                try:
                    link = next(self._iter)
                except StopIteration:
                    return None
            else:
                link = choice(self.destacados)
            data = self.article_manager.get_item(link)
            if data:
                break

            # destacado roto :|
            if self.verbose:
                print("WARNING: Artículo destacado no encontrado: %s" % link).encode("utf-8")
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
            if self.verbose:
                print("WARNING: Este articulo rompe la regexp para destacado: %s" % link)
            return None
        titulo, primeros_parrafos = m.groups()
        return link, titulo, primeros_parrafos
