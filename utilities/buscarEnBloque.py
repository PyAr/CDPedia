# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.getcwd())

import optparse

from src.armado.compresor import ArticleManager, ImageManager

def main(manager, nom_item, verbose):
    info = manager.get_item(nom_item)
    if info is None:
        print "No se encontró el item"
    else:
        print "Largo item devuelto", len(info)
        if verbose:
            print "Artículo:\n", repr(info)


if __name__ == "__main__":
    msg = u"""
  buscarEnBloque.py [-v] [-i] nombre_item
"""

    parser = optparse.OptionParser()
    parser.set_usage(msg)
    parser.add_option("-v", "--verbose", action="store_true",
                  dest="verbose", help="muestra info de lo que va haciendo")

    parser.add_option("-i", "--image", action="store_true", dest="image",
                  help=u"busca en imagenes (busca artículos por default)")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        exit()

    nom_item = args[0].decode("utf8")
    verbose = bool(options.verbose)
    if options.image:
        manager = ImageManager(verbose=verbose)
    else:
        manager = ArticleManager(verbose=verbose)

    main(manager, nom_item, verbose)

