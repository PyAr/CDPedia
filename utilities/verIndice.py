# -*- encoding: utf8 -*-

"""
Muestra info del índice.
"""

import sys
import os
sys.path.append(os.path.abspath("."))

from src.armado.cdpindex import IndexInterface

def main(direct, palabras):
    indice = IndexInterface(direct)

    if not palabras:
        for palabra, data in indice.listar():
            print "%s: %s" % (palabra, data)
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
