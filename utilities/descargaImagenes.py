# -*- encoding: utf8 -*-

"""
Descarga las imágenes cuyas URLs se extrajeron de las páginas
"""

import sys, os

sys.path.append(os.path.abspath("."))
import src.imagenes.download

def main():
    src.imagenes.download.traer(True)

if __name__ == "__main__":
    main()
