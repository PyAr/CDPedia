# -*- encoding: utf8 -*-

# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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

"""
Muestra info del índice.
"""

import sys
import os
sys.path.append(os.path.abspath("."))

from src.armado.cdpindex import IndexInterface

def main(direct, palabras):
    indice = IndexInterface(direct)
    indice.run()
    indice.ready.wait()

    if not palabras:
        for palabra, data in indice.listar():
            print "%s: %s" % (palabra.encode("utf8"), data)
    else:
        encontrado = indice.search(" ".join(palabras))
        for it in encontrado:
            print it


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usar:  verIndice.py <dir_indice> [palabra [...]]"
        print "           dir_indice es el dir donde está el índice"
        print "           las palabras opcionales son buscadas en el índice"
        sys.exit()

    base = sys.argv[1]
    palabras = [x.decode("utf8") for x in sys.argv[2:]]
    main(base, palabras)
