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

from src import utiles
from lru_cache import lru_cache

# This is the total blocks that are keep open using a LRU cache. This number
# must be less than the maximum number of files open per process.
# The most restricted system appears to be windows with 512 files per proocess.
BLOCKS_CACHE_SIZE = 100

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
        fname = os.path.join(self.archive_dir, 'numbloques.txt')
        self.num_bloques = int(open(fname).read().strip())
        self.verbose = verbose

        # get the language of the blocks, if any
        _lang_fpath = os.path.join(self.archive_dir, 'language.txt')
        if os.path.exists(_lang_fpath):
            with open(_lang_fpath, 'rt') as fh:
                self.language = fh.read().strip()
        else:
            self.language = None

    @classmethod
    def _prep_archive_dir(self, lang=None):
        # preparamos el dir destino
        if os.path.exists(self.archive_dir):
            shutil.rmtree(self.archive_dir)
        os.makedirs(self.archive_dir)

        # save the language of the blocks, if any
        if lang is not None:
            _lang_fpath = os.path.join(self.archive_dir, 'language.txt')
            with open(_lang_fpath, 'wt') as fh:
                fh.write(lang + '\n')

    @classmethod
    def guardarNumBloques(self, cant):
        """Guarda a disco la cantidad de bloques."""
        fname = os.path.join(self.archive_dir, 'numbloques.txt')
        f = open(fname, 'w')
        f.write(str(cant) + '\n')
        f.close()

    @lru_cache(BLOCKS_CACHE_SIZE) # This LRU is shared between inherited managers
    def getBloque(self, nombre):
        comp = self.archive_class(os.path.join(self.archive_dir, nombre),
                                  self.verbose, self)
        if self.verbose:
            print "block opened from file:", nombre
        return comp

    def get_item(self, fileName):
        bloqNum = utiles.coherent_hash(fileName.encode('utf8')) % self.num_bloques
        bloqName = "%08x%s" % (bloqNum, self.archive_extension)
        if self.verbose:
            print "block:", bloqName
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

    def close(self):
        """Cleanup."""
        if hasattr(self, "fh"):
            if self.verbose:
                print "closing block: ", self.fh.name
            self.fh.close()

class BloqueImagenes(Bloque):
    """Un bloque de imágenes.

    En este bloque el header va comprimido con bz2, pero tanto el tamaño del
    header, como las imágenes en sí, van sin comprimir.
    """
    def __init__(self, fname, verbose=False, manager=None):
        if os.path.exists(fname):
            self.fh = open(fname, "rb")
            self.header_size = struct.unpack("<l", self.fh.read(4))[0]
            header_bytes = self.fh.read(self.header_size)
            self.header = pickle.loads(bz2.decompress(header_bytes))
        else:
            # no hace falta definir self.fh ni self.header_size porque no va
            # a llegar a usarlo porque nunca va a tener el item en el header
            self.header = {}
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
        if os.path.exists(fname):
            self.fh = CompressedFile(fname, "rb")
            self.header_size = struct.unpack("<l", self.fh.read(4))[0]
            header_bytes = self.fh.read(self.header_size)
            self.header = pickle.loads(header_bytes)
        else:
            # no hace falta definir self.fh ni self.header_size porque no va
            # a llegar a usarlo porque nunca va a tener el item en el header
            self.header = {}
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
    def generar_bloques(self, lang, verbose):
        self._prep_archive_dir(lang)

        # lo importamos acá porque no es necesario en producción
        from src.preproceso import preprocesar

        # pedir todos los articulos, y ordenarlos en un dict por
        # su numero de bloque, segun el hash
        fileNames = preprocesar.pages_selector.top_pages
        if verbose:
            print "Procesando", len(fileNames), "articulos"

        numBloques = len(fileNames) // self.items_per_block + 1
        self.guardarNumBloques(numBloques)
        bloques = {}
        all_filenames = set()
        for dir3, fileName, _ in fileNames:
            all_filenames.add(fileName)
            bloqNum = utiles.coherent_hash(fileName.encode('utf8')) % numBloques
            bloques.setdefault(bloqNum, []).append((dir3, fileName))
            if verbose:
                print "  archs:", bloqNum, repr(dir3), repr(fileName)

        # armo el diccionario de redirects, también separados por bloques para
        # saber a dónde buscarlos
        redirects = {}
        for linea in codecs.open(config.LOG_REDIRECTS, "r", "utf-8"):
            orig, dest = linea.strip().split(config.SEPARADOR_COLUMNAS)

            # solamente nos quedamos con este redirect si realmente apunta a
            # un artículo útil (descartando el 'fragment' si hubiera)
            only_name = dest.split("#")[0]
            if only_name not in all_filenames:
                continue

            # metemos en bloque
            bloqNum = utiles.coherent_hash(orig.encode('utf8')) % numBloques
            redirects.setdefault(bloqNum, []).append((orig, dest))
            if verbose:
                print "  redirs:", bloqNum, repr(orig), repr(dest)

        # armamos cada uno de los comprimidos
        tot_archs = 0
        tot_redirs = 0
        for bloqNum, fileNames in bloques.items():
            tot_archs += len(fileNames)
            redirs_thisblock = redirects.get(bloqNum, [])
            tot_redirs += len(redirs_thisblock)
            Comprimido.crear(redirs_thisblock, bloqNum, fileNames, verbose)

        return (len(bloques), tot_archs, tot_redirs)

    def get_item(self, name):
        article = super(ArticleManager, self).get_item(name)

        # check for unicode before decoding, as we may be here twice in
        # the case of articles that are redirects to others (so, let's avoid
        # double decoding!)
        if article is not None and isinstance(article, str):
            article = article.decode("utf-8")
        return article


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
        self.guardarNumBloques(numBloques)
        bloques = {}
        for fileName in fileNames:
            bloqNum = utiles.coherent_hash(fileName.encode('utf8')) % numBloques
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
