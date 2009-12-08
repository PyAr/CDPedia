# -*- coding: utf8 -*-

"""
Compresor de los archivos crudos a los archivos de bloques.

Formato del bloque:

    4 bytes: Longitud del header

    Header: pickle de un diccionario:
             clave -> nombre del archivo original (como unicode)
             valor -> si es string, el nombre del archivo real (es un redirect)
                      si no es string, es una tupla (posición, tamaño)

    Artículos, uno detrás del otro (el origen es 0 despues del header)
"""

from __future__ import division

import os
import codecs
import struct
import cPickle as pickle
from os import path
from bz2 import BZ2File as CompressedFile
import random
import shutil

import config

class ArticleManager(object):
    def __init__(self, verbose=False):
        self.num_bloques = len(
            [n for n in os.listdir(config.DIR_BLOQUES) if n[-4:]==".cdp"])
        self.cache = {}
        self.verbose = verbose

    def getComprimido(self, nombre):
        try:
            comp = self.cache[nombre]
        except KeyError:
            comp = Comprimido(config.DIR_BLOQUES + nombre, self.verbose, self)
            self.cache[nombre] = comp
        return comp

    def getArticle(self, fileName):
        bloqNum = hash(fileName) % self.num_bloques
        bloqName = "%08x" % bloqNum
        if self.verbose:
            print "bloque:", bloqName
        comp = self.getComprimido("/%s.cdp" % bloqName)
        art = comp.get_articulo(fileName)
        return art


class Comprimido(object):
    def __init__(self, fname, verbose=False, artcl_mger=None):
        self.fh = CompressedFile(fname, "rb")
        self.header_size = struct.unpack("<l", self.fh.read(4))[0]
        header_bytes = self.fh.read(self.header_size)
        self.header = pickle.loads(header_bytes)
        self.verbose = verbose
        self.artcl_mger = artcl_mger

    @classmethod
    def crear(self, redirects, bloqNum, fileNames, verbose=False):
        '''Genera el comprimido.'''
        if verbose:
            print "Procesando el bloque", bloqNum

        header = {}

        # Llenamos el header con archivos reales, con la pag como
        # clave, y la posición/tamaño como valor, a menos que sea un
        # redirect (en ese caso, ponemos el nombre de la página a la que
        # se redirecciona
        seek = 0
        for dir3, fileName in fileNames:
            if fileName in redirects:
                # si es redirect, ponemos todos los redirects que apunten a
                # el html que guardamos
                for orig in redirects[fileName]:
                    header[orig] = fileName

            # guardamos el archivo real
            fullName = path.join(config.DIR_PAGSLISTAS, dir3, fileName)
            size = path.getsize(fullName)
            header[fileName] = (seek, size)
            seek += size

        headerBytes = pickle.dumps(header)
        if verbose:
            print "  archivos: %d   seek total: %d   largo header: %d" % (
                                    len(fileNames), seek, len(headerBytes))

        # abro el archivo a comprimir
        nomfile = path.join(config.DIR_BLOQUES, "%08x.cdp" % bloqNum)
        if verbose:
            print "  grabando en", nomfile
        f = CompressedFile(nomfile, "wb")

        # grabo la longitud del header, y el header
        f.write( struct.pack("<l", len(headerBytes) ) )
        f.write( headerBytes )

        # grabo cada uno de los articulos
        for dir3, fileName in fileNames:
            fullName = path.join(config.DIR_PAGSLISTAS, dir3, fileName)
            f.write(open( fullName, "rb" ).read())

    def get_articulo(self, fileName):
        '''Devuelve el artículo si está, sino None.'''
        if fileName not in self.header:
            return None

        info = self.header[fileName]
        if self.verbose:
            print "encontrado:", info
        if isinstance(info, basestring):
            # info es un link a lo real, hacemos semi-recursivo
            if self.verbose:
                print "redirect!"
            data = self.artcl_mger.getArticle(info)
        else:
            (seek, size) = info
            self.fh.seek(4 + self.header_size + seek)
            data = self.fh.read(size)
        return data


def generar(verbose):
    # lo importamos acá porque no es necesario en producción
    from src.preproceso import preprocesar

    import cProfile

    # preparamos el dir destino
    dest = path.join(config.DIR_BLOQUES)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)

    # pedir todos los articulos, y ordenarlos en un dict por
    # su numero de bloque, segun el hash
    fileNames = list(preprocesar.get_top_htmls(config.LIMITE_PAGINAS))
    if verbose:
        print "Procesando", len(fileNames), "articulos"

    numBloques = len(fileNames) // config.ARTICLES_PER_BLOCK + 1
    bloques = {}
    for dir3, fileName, _ in fileNames:
        if verbose:
            print "  archs:", repr(dir3), repr(fileName)
        bloqNum = hash(fileName) % numBloques
        if bloqNum not in bloques:
            bloques[bloqNum] = []
        bloques[bloqNum].append((dir3,fileName))

    # armo el diccionario de redirects
    redirects = {}
    for linea in codecs.open(config.LOG_REDIRECTS, "r", "utf-8"):
        orig, dest = linea.strip().split(config.SEPARADOR_COLUMNAS)
        redirects.setdefault(dest, []).append(orig)
        if verbose:
            print "  redirs:", repr(orig), repr(dest)

    # armamos cada uno de los comprimidos
    tot = 0
    for bloqNum, fileNames in bloques.items():
        tot += len(fileNames)
        Comprimido.crear(redirects, bloqNum, fileNames, verbose)

    return (len(bloques), tot)

if __name__ == "__main__":
    generar()
