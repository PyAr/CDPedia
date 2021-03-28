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
Show index info.
"""

from __future__ import division, with_statement, print_function

import sys
import os
import time
import random
import functools
import subprocess

sys.path.append(os.path.abspath("."))
from src.armado.cdpindex import IndexInterface  # NOQA import after fixing path

BLOQUE = 20


class Timer(object):
    def __init__(self, msg, divisor=1):
        self.msg = msg
        self.divisor = divisor

    def __enter__(self):
        self.t = time.time()

    def __exit__(self, *args):
        tnow = time.time()
        mseg = 1000 * (tnow - self.t) / self.divisor
        print("%8.1fms  %s" % (mseg, self.msg))
        self.t = tnow


def memoryUsage():
    pid = os.getpid()
    cmd = "ps -o vsize=,rss= -p " + str(pid)
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    info = p.stdout.read()
    v, r = map(int, info.strip().split())
    return v + r


def main(direct):
    memant = memoryUsage()
    with Timer("Start up"):
        indice = IndexInterface(direct)
        indice.run()
        indice.ready.wait()
    memdesp = memoryUsage()

    print("               occupy memory:  %d KB" % (memdesp - memant))

    with Timer("Full list of words"):
        palabras = [x.decode("utf8") for x in indice.listado_palabras()]
    print("               cant words:", len(palabras))

    # complete words
    azar = functools.partial(random.choice, palabras)

    # get the results
    pals = [azar() for i in range(BLOQUE)]
    with Timer("Search for complete words, and get the result", BLOQUE):
        for p in pals:
            list(indice.search(p))

    # complete words, from to one
    pals = [azar() for i in range(BLOQUE)]
    with Timer("Complete words, from to one", BLOQUE):
        for p in pals:
            indice.search(p)

    # complete words, from to 2
    pals = ["%s %s" % (azar(), azar()) for i in range(BLOQUE)]
    with Timer("Complete words, from to 2", BLOQUE):
        for p in pals:
            indice.search(p)

    # complete words, from to 5
    pals = [("%s " * 5) % tuple(azar() for j in range(5)) for i in range(BLOQUE)]
    with Timer("Complete words, from to 5", BLOQUE):
        for p in pals:
            indice.search(p)

    # partial words
    def azar():
        pal = None
        while not pal:
            pal = random.choice(palabras)
            largo = len(pal)
            desde = random.randint(0, largo // 2)
            hasta = largo - random.randint(0, largo // 2)
            pal = pal[desde:hasta]
        return pal

    # partial words, from to one
    pals = [azar() for i in range(BLOQUE)]
    with Timer("Partial words, from to one", BLOQUE):
        for p in pals:
            indice.partial_search(p)

    # partial words, from to 2
    pals = ["%s %s" % (azar(), azar()) for i in range(BLOQUE)]
    with Timer("Partial words, from to 2", BLOQUE):
        for p in pals:
            indice.partial_search(p)

    # partial words, from to 5
    pals = [("%s " * 5) % tuple(azar() for j in range(5)) for i in range(BLOQUE)]
    with Timer("Partial words, from to 5", BLOQUE):
        for p in pals:
            indice.partial_search(p)

    memdesp = memoryUsage()
    print("\nNew memory usage:  %d KB" % (memdesp - memant))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use:  benchmarkIndice.py <dir_index>")
        print("           dir_index is the directory where is the index")
        sys.exit()

    base = sys.argv[1]
    main(base)
