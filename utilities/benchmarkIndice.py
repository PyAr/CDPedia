# -*- encoding: utf8 -*-

"""
Muestra info del índice.
"""

from __future__ import division
from __future__ import with_statement

import sys
import os
import time
import random
import functools
sys.path.append(os.path.abspath("."))

from src.armado.cdpindex import Index

BLOQUE = 100

class Timer(object):
    def __init__(self, msg, divisor=1):
        self.msg = msg
        self.divisor = divisor

    def __enter__(self):
        self.t = time.time()

    def __exit__(self, *args):
        tnow = time.time()
        mseg = 1000 * (tnow-self.t) / self.divisor
        print "%8.1fms  %s" % (mseg, self.msg)
        self.t = tnow

def main(arch_ind):
    with Timer("Start up"):
        indice = Index(arch_ind)

    with Timer("Listado completo"):
        listado = indice.listado_completo()

    palabras = set()
    for (pag, tit) in listado:
        palabras.update(set(tit.split()))
    palabras = list(palabras)

    # palabras completas
    azar = functools.partial(random.choice, palabras)

    # palabras completas, de a una
    pals = [azar() for i in range(BLOQUE)]
    with Timer("Palabras completas, de a una", BLOQUE):
        for p in pals:
            indice.search(p)

    # palabras completas de a 2
    pals = ["%s %s" % (azar(), azar()) for i in range(BLOQUE)]
    with Timer("Palabras completas, de a 2", BLOQUE):
        for p in pals:
            indice.search(p)

    # palabras completas de a 5
    pals = [("%s "*5) % tuple(azar() for j in range(5)) for i in range(BLOQUE)]
    with Timer("Palabras completas, de a 5", BLOQUE):
        for p in pals:
            indice.search(p)

    # palabras parciales
    def azar():
        pal = None
        while not pal:
            pal = random.choice(palabras)
            largo = len(pal)
            desde = random.randint(0, largo // 2)
            hasta = largo - random.randint(0, largo // 2)
            pal = pal[desde:hasta]
        return pal

    # palabras parciales, de a una
    pals = [azar() for i in range(BLOQUE)]
    with Timer("Palabras parciales, de a una", BLOQUE):
        for p in pals:
            indice.search(p)

    # palabras parciales, de a 2
    pals = ["%s %s" % (azar(), azar()) for i in range(BLOQUE)]
    with Timer("Palabras parciales, de a 2", BLOQUE):
        for p in pals:
            indice.search(p)

    # palabras parciales, de a 5
    pals = [("%s "*5) % tuple(azar() for j in range(5)) for i in range(BLOQUE)]
    with Timer("Palabras parciales, de a 5", BLOQUE):
        for p in pals:
            indice.search(p)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usar:  verIndice.py <indice_base>"
        print "           donde el indice_base es la parte base del nombre,"
        print "           tienen que estar ambos .ids y .words"
        sys.exit()

    base = sys.argv[1]
    if not os.access("%s.ids" % base, os.R_OK):
        print "No se encontró el archivo '%s.ids'" % base
        sys.exit()
    if not os.access("%s.words" % base, os.R_OK):
        print "No se encontró el archivo '%s.words'" % base
        sys.exit()
    main(base)
