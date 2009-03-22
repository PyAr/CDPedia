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

        # arrancamos el header tomando la info de los redirects, lo que
        # nos da la pag como clave, y la pag a la que redirige como valor
        header = redirects[bloqNum]

        # seguimos llenando el header con archivos reales, con la pag como
        # clave, y la posición/tamaño como valor
        seek = 0
        for root, fileName in fileNames:
            # si ya lo pusimos como redirect, no lo ponemos como archivo real
            if fileName in header:
                continue

            fullName = path.join(root, fileName)
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
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
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
    # preparamos el dir destino
    dest = path.join(config.DIR_BLOQUES)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)

    # recorrer todos los nombres de articulos, y ordenarlos en un dict por
    # su numero de bloque, segun el hash
    fileNames = []
    if verbose:
        print "Buscando los artículos"
    for root, dirs, files in os.walk(unicode(config.DIR_PREPROCESADO)):
        for fileName in files:
            fileNames.append( (root, fileName) )
            if len(fileNames)%10000 == 0:
                if verbose:
                    print "  encontrados %d artículos" % len(fileNames)

    if verbose:
        print "Procesando", len(fileNames), "articulos"
    numBloques= max(len(fileNames) // config.ARTICLES_PER_BLOCK, 1)
    bloques = {}
    for root, fileName in fileNames:
        if verbose:
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
        if verbose:
            print "  redirs:", desde, hasta
        bloqNum = hash(desde) % numBloques
        redirects[bloqNum][desde] = hasta

    # armamos cada uno de los comprimidos
    tot = 0
    for bloqNum, fileNames in bloques.items():
        tot += len(fileNames)
        Comprimido.crear(redirects, bloqNum, fileNames, verbose)
    return (len(bloques), tot)

if __name__ == "__main__":
    generar()
