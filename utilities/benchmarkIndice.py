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
import subprocess

sys.path.append(os.path.abspath("."))
from src.armado.cdpindex import IndexInterface

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

def usoMemoria():
    pid = os.getpid()
    cmd = "ps -o vsize=,rss= -p " + str(pid)
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    info = p.stdout.read()
    v,r = map(int, info.strip().split())
    return v + r

def main(direct):
    memant = usoMemoria()
    with Timer("Start up"):
        indice = IndexInterface(direct)
    memdesp = usoMemoria()

    print "               cant palabras:", len(list(indice.listar()))
    print "               ocupa memoria:  %d KB" % (memdesp - memant)

    with Timer("Listado completo"):
        listado = indice.listado_valores()

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
            indice.partial_search(p)

    # palabras parciales, de a 2
    pals = ["%s %s" % (azar(), azar()) for i in range(BLOQUE)]
    with Timer("Palabras parciales, de a 2", BLOQUE):
        for p in pals:
            indice.partial_search(p)

    # palabras parciales, de a 5
    pals = [("%s "*5) % tuple(azar() for j in range(5)) for i in range(BLOQUE)]
    with Timer("Palabras parciales, de a 5", BLOQUE):
        for p in pals:
            indice.partial_search(p)

    memdesp = usoMemoria()
    print "\nNuevo consumo de memoria:  %d KB" % (memdesp - memant)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usar:  benchmarkIndice.py <dir_indice>"
        print "           dir_indice es el directorio donde está el índice"
        sys.exit()

    base = sys.argv[1]
    main(base)
