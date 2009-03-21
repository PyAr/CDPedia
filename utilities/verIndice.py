# -*- encoding: utf8 -*-

"""
Muestra info del índice.
"""

import sys
import os
sys.path.append(os.path.abspath("."))

from src.armado.cdpindex import Index

def main(arch_ind, palabras):
    indice = Index(arch_ind)

    if not palabras:
        indice.listar()
    else:
        encontrado = indice.search(*palabras)
        for it in encontrado:
            print it


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usar:  verIndice.py <indice_base> [palabra [...]]"
        print "           donde el indice_base es la parte base del nombre,"
        print "           tienen que estar ambos .ids y .words"
        print "           Las palabras opcionales son buscadas en el índice"
        sys.exit()

    base = sys.argv[1]
    if not os.access("%s.ids" % base, os.R_OK):
        print "No se encontró el archivo '%s.ids'" % base
        sys.exit()
    if not os.access("%s.words" % base, os.R_OK):
        print "No se encontró el archivo '%s.words'" % base
        sys.exit()

    palabras = [x.decode("utf8") for x in sys.argv[2:]]
    main(base, palabras)
