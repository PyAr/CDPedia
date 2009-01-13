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
import config

class ArticleManager(object):
    def __init__(self):
        self.num_bloques = len(
            [n for n in os.listdir(config.DIR_BLOQUES) if n[-4:]==".cdp"])
        self.cache = {}

    def getComprimido(self, nombre):
        try:
            comp = self.cache[nombre]
        except KeyError:
            comp = Comprimido(config.DIR_BLOQUES + nombre)
            self.cache[nombre] = comp
        return comp

    def getArticle(self, fileName):
        bloqNum = hash(fileName) % self.num_bloques
        bloqName = "%08x" % bloqNum
        comp = self.getComprimido("/%s.cdp" % bloqName)
        art = comp.get_articulo(fileName)
        return art


class Comprimido(object):
    def __init__(self, fname):
        self.fh = CompressedFile(fname, "rb")
        self.header_size = struct.unpack("<l", self.fh.read(4))[0]
        header_bytes = self.fh.read(self.header_size)
        self.header = pickle.loads(header_bytes)

    @classmethod
    def crear(self, redirects, bloqNum, fileNames):
        '''Genera el comprimido.'''
        print "Procesando el bloque", bloqNum

        # armo el header con un ejemplo de redirect
        header = redirects[bloqNum]
        seek = 0
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
            size = path.getsize(fullName)
            header[fileName.encode("utf-8")] = (seek, size)
            seek += size
        headerBytes = pickle.dumps(header)
        print "  archivos: %d   seek total: %d   largo header: %d" % (
                                    len(fileNames), seek, len(headerBytes))

        # abro el archivo a comprimir
        nomfile = path.join(config.DIR_BLOQUES, "%08x.cdp" % bloqNum)
        print "  grabando en", nomfile
        f = CompressedFile(nomfile, "wb")

        # grabo la longitud del header, y el header
        f.write( struct.pack("<l", len(headerBytes) ) )
        f.write( headerBytes )

        # grabo cada uno de los articulos
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
            f.write(open( fullName, "rb" ).read())

    def get_articulo(self, fileName):
        '''Devuelve el artículo si está, sino None.'''
        if fileName not in self.header:
            return None

        info = self.header[fileName]
        if isinstance(info, basestring):
            # info es un link a lo real, hacemos semi-recursivo
            data = getArticle(info)
        else:
            (seek, size) = info
            self.fh.seek(4 + self.header_size + seek)
            data = self.fh.read(size)
        return data



def generar():
    # recorrer todos los nombres de articulos, y ordenarlos en un dict por
    # su numero de bloque, segun el hash
    fileNames = []
    print "Buscando los artículos"
    for root, dirs, files in os.walk(unicode(config.DIR_PREPROCESADO)):
        for fileName in files:
            fileNames.append( (root, fileName) )
            if len(fileNames)%10000 == 0:
                print "  encontrados %d artículos" % len(fileNames)

    print "Procesando", len(fileNames), "articulos"
    numBloques= max(len(fileNames) // config.ARTICLES_PER_BLOCK, 1)
    bloques = {}
    for root, fileName in fileNames:
        print "  archs:", root, fileName
        bloqNum = hash(fileName) % numBloques
        if bloqNum not in bloques:
            bloques[bloqNum] = []
        bloques[bloqNum].append((root,fileName))

    # armo el diccionario de redirects
    redirects = dict( (n,{}) for n in range(numBloques) )
    for linea in codecs.open(config.LOG_REDIRECTS, "r", "utf-8"):
        desde, hasta = linea.split()
        desde = path.basename(desde)
        hasta = path.basename(hasta)
        print "  redirs:", desde, hasta
        bloqNum = hash(desde) % numBloques
        redirects[bloqNum][desde] = hasta

    # armamos cada uno de los comprimidos
    for bloqNum, fileNames in bloques.items():
        Comprimido.crear(redirects, bloqNum, fileNames)

if __name__ == "__main__":
    generar()
