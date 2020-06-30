# -*- coding: utf8 -*-

# Copyright 2008-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/

"""
Compressor of the raw content (files, images) to the block files.

Format of the block:

    - 4 bytes: header length

    - header: pickle of a dict:
        key -> name of the original file (unicode!)
        value -> if string, it's a redirect, pointing to the real file name
                 otherwise it's a (position, size) tuple

    - all the articles, smashed one after the other (origin 0 is after the header)
"""

import bz2
import logging
import os
import pickle
import shutil
import struct
from bz2 import BZ2File as CompressedFile
from functools import lru_cache
from os import path

import config
from src import utiles


logger = logging.getLogger(__name__)

# This is the total blocks that are keep open using a LRU cache. This number
# must be less than the maximum number of files open per process.
# The most restricted system appears to be windows with 512 files per proocess.
BLOCKS_CACHE_SIZE = 100


class BloqueManager(object):
    """Base class for the blockfiles handlers; not intended to be used directly.

    It has two very similar children, ArticleManager y ImageManager, which define
    the needing working constants.
    """
    archive_dir = None  # the directory with all the blocks
    archive_extension = ".hdp"  # extension of the blocks handled by this class
    archive_class = None  # class to be used for the blcoks
    items_per_block = 0  # quantity of items per block

    def __init__(self, verbose=False):
        fname = os.path.join(self.archive_dir, 'numbloques.txt')
        with open(fname, 'rt', encoding='ascii') as fh:
            self.num_bloques = int(fh.read().strip())
        self.verbose = verbose

        # get the language of the blocks, if any
        _lang_fpath = os.path.join(self.archive_dir, 'language.txt')
        if os.path.exists(_lang_fpath):
            with open(_lang_fpath, 'rt', encoding='utf8') as fh:
                self.language = fh.read().strip()
        else:
            self.language = None

    @classmethod
    def _prep_archive_dir(self, lang=None):
        """Prepare the directory for the archive."""
        # prepare the destination dir
        if os.path.exists(self.archive_dir):
            shutil.rmtree(self.archive_dir)
        os.makedirs(self.archive_dir)

        # save the language of the blocks, if any
        if lang is not None:
            _lang_fpath = os.path.join(self.archive_dir, 'language.txt')
            with open(_lang_fpath, 'wt', encoding='utf8') as fh:
                fh.write(lang + '\n')

    @classmethod
    def guardarNumBloques(self, cant):
        """Save to disk the quantity of blocks."""
        fname = os.path.join(self.archive_dir, 'numbloques.txt')
        with open(fname, 'wt', encoding='ascii') as fh:
            fh.write(str(cant) + '\n')

    @lru_cache(BLOCKS_CACHE_SIZE)  # This LRU is shared between inherited managers
    def getBloque(self, nombre):
        """Get the block for a given name."""
        comp = self.archive_class(os.path.join(self.archive_dir, nombre), self.verbose, self)
        logger.debug("block opened from file: %s", nombre)
        return comp

    def get_item(self, fileName):
        """Get the item from inside of a block."""
        bloqNum = utiles.coherent_hash(fileName.encode('utf8')) % self.num_bloques
        bloqName = "%08x%s" % (bloqNum, self.archive_extension)
        logger.debug("block: %s", bloqName)
        comp = self.getBloque(bloqName)
        item = comp.get_item(fileName)
        logger.debug("len item: %s", None if item is None else len(item))
        return item


class Bloque(object):
    """Common functionality for a block."""

    def get_item(self, fileName):
        """Return the item if present, else None."""
        if fileName not in self.header:
            return None

        info = self.header[fileName]
        logger.debug("found: %s", info)
        if isinstance(info, str):
            # info is a link to the real page, let's go semi-recursive
            logger.debug("redirect!")
            data = self.manager.get_item(info)
        else:
            (seek, size) = info
            self.fh.seek(4 + self.header_size + seek)
            data = self.fh.read(size)
        return data

    def close(self):
        """Cleanup."""
        if hasattr(self, "fh"):
            logger.debug("closing block: %s", self.fh.name)
            self.fh.close()


class BloqueImagenes(Bloque):
    """A block of images.

    Here the header is compressed with bz2, but the header size and the images are not.
    """
    def __init__(self, fname, verbose=False, manager=None):
        if os.path.exists(fname):
            self.fh = open(fname, "rb")
            self.header_size = struct.unpack("<l", self.fh.read(4))[0]
            header_bytes = self.fh.read(self.header_size)
            self.header = pickle.loads(bz2.decompress(header_bytes))
        else:
            # no need to define self.fh or self.header_size because will never be
            # used, as no item will be found in the empty header
            self.header = {}
        self.verbose = verbose
        self.manager = manager

    @classmethod
    def crear(self, bloqNum, fileNames, verbose=False):
        """Generate the file."""
        logger.debug("Processing block of images %s", bloqNum)

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
        logger.debug(
            "  files: %d   total seek: %d   header length: %d",
            len(fileNames), seek, len(headerBytes))

        # open the file to compress
        nomfile = os.path.join(config.DIR_ASSETS, 'images', "%08x.cdi" % bloqNum)
        logger.debug("  saving in %s", nomfile)

        with open(nomfile, "wb") as dst_fh:
            # save the header length and the header itself
            dst_fh.write(struct.pack("<l", len(headerBytes)))
            dst_fh.write(headerBytes)

            # save each of the images
            for fileName in fileNames:
                fullName = os.path.join(config.DIR_IMGSLISTAS, fileName)
                with open(fullName, "rb") as src_fh:
                    dst_fh.write(src_fh.read())


class Comprimido(Bloque):
    """A block of articles.

    Here everything is compressed together.
    """

    def __init__(self, fname, verbose=False, manager=None):
        if os.path.exists(fname):
            self.fh = CompressedFile(fname, "rb")
            self.header_size = struct.unpack("<l", self.fh.read(4))[0]
            header_bytes = self.fh.read(self.header_size)
            self.header = pickle.loads(header_bytes)
        else:
            # no need to define self.fh or self.header_size because will never be
            # used, as no item will be found in the empty header
            self.header = {}
        self.verbose = verbose
        self.manager = manager

    @classmethod
    def crear(self, redirects, bloqNum, top_filenames, verbose=False):
        """Generate the compressed file."""
        logger.debug("Processing block %s", bloqNum)

        header = {}

        # fill the header with real file info, with the page as key, and the position/size as value
        seek = 0
        for dir3, filename in top_filenames:
            fullName = path.join(config.DIR_PAGSLISTAS, dir3, filename)
            size = path.getsize(fullName)
            header[filename] = (seek, size)
            seek += size

        # put also in the header the redirects, being the value the page that is destination of
        # the redirection
        for orig, dest in redirects:
            header[orig] = dest

        headerBytes = pickle.dumps(header)
        logger.debug(
            "  files: %d   total seek: %d   header length: %d",
            len(top_filenames), seek, len(headerBytes))

        # open the compressed file
        nomfile = path.join(config.DIR_BLOQUES, "%08x.cdp" % bloqNum)
        logger.debug("  saving in %s", nomfile)

        with CompressedFile(nomfile, "wb") as dst_fh:
            # save the header length, and the header itself
            dst_fh.write(struct.pack("<l", len(headerBytes)))
            dst_fh.write(headerBytes)

            # save each of the articles
            for dir3, filename in top_filenames:
                fullName = path.join(config.DIR_PAGSLISTAS, dir3, filename)
                with open(fullName, "rb") as src_fh:
                    dst_fh.write(src_fh.read())


class ArticleManager(BloqueManager):
    archive_dir = config.DIR_BLOQUES
    archive_extension = ".cdp"
    archive_class = Comprimido
    items_per_block = config.ARTICLES_PER_BLOCK

    @classmethod
    def generar_bloques(self, lang, verbose):
        self._prep_archive_dir(lang)

        # import this here as it's not needed in production
        from src.preprocessing import preprocess

        # get all the articles, and store them in a dict using its block number, calculated
        # wiht a hash of the name
        top_pages = preprocess.pages_selector.top_pages
        logger.debug("Processing %d articles", len(top_pages))

        numBloques = len(top_pages) // self.items_per_block + 1
        self.guardarNumBloques(numBloques)
        bloques = {}
        all_filenames = set()
        for dir3, filename, _ in top_pages:
            all_filenames.add(filename)
            bloqNum = utiles.coherent_hash(filename.encode('utf8')) % numBloques
            bloques.setdefault(bloqNum, []).append((dir3, filename))
            logger.debug("  files: %s %r %r", bloqNum, dir3, filename)

        # build the redirect dict, also separated by blocks to know where to find them
        redirects = {}
        for linea in open(config.LOG_REDIRECTS, "rt", encoding="utf-8"):
            orig, dest = linea.strip().split(config.SEPARADOR_COLUMNAS)

            # only keep this redirect if really points to an useful article (discarding any
            # possible 'fragment')
            only_name = dest.split("#")[0]
            if only_name not in all_filenames:
                continue

            # put it in a block
            bloqNum = utiles.coherent_hash(orig.encode('utf8')) % numBloques
            redirects.setdefault(bloqNum, []).append((orig, dest))
            logger.debug("  redirs: %s %r %r", bloqNum, orig, dest)

        # build each of the compressed blocks
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
        if article is not None and isinstance(article, bytes):
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

        # get all the images, and store them in a dict using its block number, calculated
        # wiht a hash of the name
        fileNames = []
        for dirname, subdirs, files in os.walk(config.DIR_IMGSLISTAS):
            for f in files:
                name = os.path.join(dirname, f)[len(config.DIR_IMGSLISTAS) + 1:]
                fileNames.append(name)
        logger.debug("Processing %d images", len(fileNames))

        numBloques = len(fileNames) // self.items_per_block + 1
        self.guardarNumBloques(numBloques)
        bloques = {}
        for fileName in fileNames:
            bloqNum = utiles.coherent_hash(fileName.encode('utf8')) % numBloques
            bloques.setdefault(bloqNum, []).append(fileName)
            logger.debug("  files:", bloqNum, repr(fileName))

        tot = 0
        for bloqNum, fileNames in bloques.items():
            tot += len(fileNames)
            BloqueImagenes.crear(bloqNum, fileNames, verbose)

        return (len(bloques), tot)
