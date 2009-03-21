# -*- coding: utf8 -*-

import sys
import os
sys.path.append(os.getcwd())

import optparse

from src.armado import compresor

def main(nomart, verbose):
    _art_mngr = compresor.ArticleManager(verbose=True)
    info = _art_mngr.getArticle(nomart)
    if info is None:
        print "No se encontró el artículo"
    else:
        print "Largo artículo devuelto", len(info)
        if verbose:
            print "Artículo:\n", repr(info)


if __name__ == "__main__":
    msg = u"""
  buscarEnBloque.py [-v] nombre_articulo
"""

    parser = optparse.OptionParser()
    parser.set_usage(msg)
    parser.add_option("-v", "--verbose", action="store_true",
                  dest="verbose", help="muestra info de lo que va haciendo")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        exit()

    nomart = args[0]
    verbose = bool(options.verbose)

    main(nomart, verbose)

