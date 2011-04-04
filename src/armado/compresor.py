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

import bz2
import os
import codecs
import struct
import cPickle as pickle
from os import path
from bz2 import BZ2File as CompressedFile
import shutil

import config


class BloqueManager(object):
    """Clase base para los manejadores de bloques de archivos.

    No se usa directamente.
    Tiene dos hijos muy parecidos, ArticleManager y ImageManager, que definen
    las constantes necesarias para poder funcionar.
    """
    archive_dir = None # Esto deberia apuntar al dir donde estan los bloques
    archive_extension = ".hdp" # Extension de los bloques que maneja esto
    archive_class = None # La clase que se va a usar para los  bloques
    items_per_block = 0 # Cantidad de items por bloque

    def __init__(self, verbose=False):
        self.num_bloques = len(
            [n for n in os.listdir(self.archive_dir)
                if n.endswith(self.archive_extension)])
        self.cache = {}
        self.verbose = verbose

    @classmethod
    def _prep_archive_dir(self):
        # preparamos el dir destino
        if os.path.exists(self.archive_dir):
            shutil.rmtree(self.archive_dir)
        os.makedirs(self.archive_dir)


    def getBloque(self, nombre):
        try:
            comp = self.cache[nombre]
        except KeyError:
            comp = self.archive_class(os.path.join(self.archive_dir, nombre),
                self.verbose, self)
            self.cache[nombre] = comp
        return comp

    def get_item(self, fileName):
        bloqNum = hash(fileName) % self.num_bloques
        bloqName = "%08x%s" % (bloqNum, self.archive_extension)
        if self.verbose:
            print "bloque:", bloqName
        comp = self.getBloque(bloqName)
        item = comp.get_item(fileName)
        if self.verbose and item is not None:
            print "len item:", len(item)
        return item


class Bloque(object):
    def get_item(self, fileName):
        '''Devuelve el item si está, sino None.'''
        if fileName not in self.header:
            return None

        info = self.header[fileName]
        if self.verbose:
            print "encontrado:", info
        if isinstance(info, basestring):
            # info es un link a lo real, hacemos semi-recursivo
            if self.verbose:
                print "redirect!"
            data = self.manager.get_item(info)
        else:
            (seek, size) = info
            self.fh.seek(4 + self.header_size + seek)
            data = self.fh.read(size)
        return data


class BloqueImagenes(Bloque):
    """Un bloque de imágenes.

    En este bloque el header va comprimido con bz2, pero tanto el tamaño del
    header, como las imágenes en sí, van sin comprimir.
    """
    def __init__(self, fname, verbose=False, manager=None):
        self.fh = open(fname, "rb")
        self.header_size = struct.unpack("<l", self.fh.read(4))[0]
        header_bytes = self.fh.read(self.header_size)
        self.header = pickle.loads(bz2.decompress(header_bytes))
        self.verbose = verbose
        self.manager = manager

    @classmethod
    def crear(self, bloqNum, fileNames, verbose=False):
        '''Genera el archivo.'''
        if verbose:
            print "Procesando el bloque de imágenes", bloqNum

        header = {}

        # Llenamos el header con archivos reales, con la imagen como
        # clave, y la posición/tamaño como valor
        seek = 0
        for fileName in fileNames:
            fullName = os.path.join(config.DIR_IMGSLISTAS, fileName)
            size = os.path.getsize(fullName)
            header[fileName] = (seek, size)
            seek += size

        headerBytes = bz2.compress(pickle.dumps(header))
        if verbose:
            print "  archivos: %d   seek total: %d   largo header: %d" % (
                    len(fileNames), seek, len(headerBytes))

        # abro el archivo a comprimir
        nomfile = os.path.join(config.DIR_ASSETS, 'images', "%08x.cdi" % bloqNum)
        if verbose:
            print "  grabando en", nomfile
        f = open(nomfile, "wb")

        # grabo la longitud del header, y el header
        f.write(struct.pack("<l", len(headerBytes)))
        f.write(headerBytes)

        # grabo cada uno de los articulos
        for fileName in fileNames:
            fullName = os.path.join(config.DIR_IMGSLISTAS, fileName)
            f.write(open(fullName, "rb").read())


class Comprimido(Bloque):
    """Un bloque de artículos.

    Este es un bloque en el que todo el archivo, header y datos por igual,
    va al disco comprimido con bz2.
    """

    def __init__(self, fname, verbose=False, manager=None):
        self.fh = CompressedFile(fname, "rb")
        self.header_size = struct.unpack("<l", self.fh.read(4))[0]
        header_bytes = self.fh.read(self.header_size)
        self.header = pickle.loads(header_bytes)
        self.verbose = verbose
        self.manager = manager

    @classmethod
    def crear(self, redirects, bloqNum, fileNames, verbose=False):
        '''Genera el comprimido.'''
        if verbose:
            print "Procesando el bloque", bloqNum

        header = {}

        # Llenamos el header con archivos reales, con la pag como
        # clave, y la posición/tamaño como valor
        seek = 0
        for dir3, fileName in fileNames:
            fullName = path.join(config.DIR_PAGSLISTAS, dir3, fileName)
            size = path.getsize(fullName)
            header[fileName] = (seek, size)
            seek += size

        # Ponemos en el header también los redirects, apuntando en este caso
        # ael nombre de la página a la que se redirecciona
        for orig, dest in redirects:
            header[orig] = dest

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


class ArticleManager(BloqueManager):
    archive_dir = config.DIR_BLOQUES
    archive_extension = ".cdp"
    archive_class = Comprimido
    items_per_block = config.ARTICLES_PER_BLOCK

    @classmethod
    def generar_bloques(self, verbose):
        self._prep_archive_dir()

        # lo importamos acá porque no es necesario en producción
        from src.preproceso import preprocesar

        # pedir todos los articulos, y ordenarlos en un dict por
        # su numero de bloque, segun el hash
        fileNames = preprocesar.get_top_htmls()
        if verbose:
            print "Procesando", len(fileNames), "articulos"

        numBloques = len(fileNames) // self.items_per_block + 1
        bloques = {}
        for dir3, fileName, _ in fileNames:
            bloqNum = hash(fileName) % numBloques
            bloques.setdefault(bloqNum, []).append((dir3, fileName))
            if verbose:
                print "  archs:", bloqNum, repr(dir3), repr(fileName)

        # armo el diccionario de redirects, también separados por bloques para
        # saber a dónde buscarlos
        redirects = {}
        for linea in codecs.open(config.LOG_REDIRECTS, "r", "utf-8"):
            orig, dest = linea.strip().split(config.SEPARADOR_COLUMNAS)
            bloqNum = hash(orig) % numBloques
            redirects.setdefault(bloqNum, []).append((orig, dest))
            if verbose:
                print "  redirs:", bloqNum, repr(orig), repr(dest)

        # armamos cada uno de los comprimidos
        tot = 0
        for bloqNum, fileNames in bloques.items():
            tot += len(fileNames)
            redirs_thisblock = redirects[bloqNum]
            Comprimido.crear(redirs_thisblock, bloqNum, fileNames, verbose)

        return (len(bloques), tot)


class ImageManager(BloqueManager):
    archive_dir = os.path.join(config.DIR_ASSETS, 'images')
    archive_extension = ".cdi"
    archive_class = BloqueImagenes
    items_per_block = config.IMAGES_PER_BLOCK

    @classmethod
    def generar_bloques(self, verbose):
        self._prep_archive_dir()

        # pedir todas las imágenes, y ordenarlos en un dict por
        # su numero de bloque, segun el hash
        fileNames = []
        for dirname, subdirs, files in os.walk(config.DIR_IMGSLISTAS):
            for f in files:
                name = os.path.join(dirname, f)[len(config.DIR_IMGSLISTAS) + 1:]
                fileNames.append(name)
        if verbose:
            print "Procesando", len(fileNames), "imágenes"

        numBloques = len(fileNames) // self.items_per_block + 1
        bloques = {}
        for fileName in fileNames:
            bloqNum = hash(fileName) % numBloques
            bloques.setdefault(bloqNum, []).append(fileName)
            if verbose:
                print "  archs:", bloqNum, repr(fileName)

        tot = 0
        for bloqNum, fileNames in bloques.items():
            tot += len(fileNames)
            BloqueImagenes.crear(bloqNum, fileNames, verbose)

        return (len(bloques), tot)


if __name__ == "__main__":
    ArticleManager.generar()
