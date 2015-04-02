# -*- coding: utf-8 -*-
import sys
import bz2
import cPickle

TRANSPARENT = '!'

def main(filename):
    f = open(filename)
    f.readline() # Descartamos el comentario
    f.readline()
    width, height, ncolors, bpc = f.readline()[1:-3].split()
    ncolors = int(ncolors)
    width = int(width)
    height = int(height)
    colors = {}
    for n in range(ncolors):
        line = f.readline()
        parts = line[1:-3].split()
        if len(parts) == 2:
            continue
        char, _, color = parts
        color = int(color[1:3], 16)
        colors[char] = color
    pixels = []
    y = height - 1
    for n in range(height):
        line = f.readline()
        cols = line[1:width + 1]
        for x, char in enumerate(cols):
            if char != TRANSPARENT:
                pixels.append((x, y, colors[char]))
        y -= 1
    data = cPickle.dumps(pixels)
    print bz2.compress(data).encode('base64')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print u"""
  %s archivo.xpm
    Convierte un xpm a un pickle bzipped en base64, como para usar en bmp.py.
    Solo funciona con xpms de un byte por pixel, y capaz con algunas
    restricciones más.
""" % sys.argv[0]
        exit()

    main(sys.argv[1])

