# -*- coding: utf8 -*-

import sys
import os
sys.path.append(os.getcwd())

from src.armado import compresor

def main(nomart):
    _art_mngr = compresor.ArticleManager(verbose=True)
    info = _art_mngr.getArticle(nomart)
    print "Largo artículo devuelto", len(info)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usar:  buscarEnBloque.py nombre_articulo"
        sys.exit()

    main(sys.argv[1])

