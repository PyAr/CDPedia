# -*- encoding: utf8 -*-

"""
Muestra info del archivo comprimido.
"""

from __future__ import division
from __future__ import with_statement

import operator
import sys
import os
sys.path.append(os.getcwd())
from src.imagenes import extraer

def main(fname):
    pi = extraer.ParseaImagenes(test=True)
    pi.parsea(fname)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usar:  parseaImagenes.py <arch.html>"
        sys.exit()

    main(sys.argv[1])
