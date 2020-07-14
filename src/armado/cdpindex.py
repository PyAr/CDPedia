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

from __future__ import print_function, unicode_literals

"""
Library to create and read index.

"""

import base64
import config
import logging
import os
import re
import shutil
import subprocess
import threading
import unicodedata

# from .easy_index import Index
# from .compressed_index import Index
from .sqlite_index import Index

logger = logging.getLogger(__name__)

# regex used to separate words
WORDS = re.compile(r"\w+", re.UNICODE)


def normalize_words(txt):
    """Separate and normalize every word from a sentence."""
    txt = unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').lower().decode("ascii")
    return txt


def _get_html_words(arch):
    # FIXME:this will be used on full text search of html
    arch = os.path.abspath(arch)
    cmd = config.CMD_HTML_A_TEXTO % arch
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    txt = p.stdout.read()
    txt = txt.decode("utf8")
    return txt


class IndexInterface(threading.Thread):
    """Process the information needed to connect with index.

    In association with every word will be saved

     - namhtml: the path to the file
     - title: the article's title
     - score: to weight the relative importance of each article
    """
    def __init__(self, directory):
        super(IndexInterface, self).__init__()
        self.ready = threading.Event()
        self.directory = directory
        self.daemon = True

    def is_ready(self):
        return self.ready.isSet()

    def run(self):
        """Starts the index."""
        self.index = Index(self.directory)
        self.ready.set()

    def listado_words(self):
        """Returns the key words."""
        self.ready.wait()
        return sorted(self.index.keys())

    def listado_valores(self):
        """Returns every article information."""
        self.ready.wait()
        return sorted(set(x[:2] for x in self.index.values()))

    def get_random(self):
        """Returns a random article."""
        self.ready.wait()
        value = self.index.random()
        return value[:2]

    def search(self, words):
        """Search whole words in the index."""
        self.ready.wait()
        return self.index.search(words)

    def partial_search(self, words):
        """Search partial words inside the index."""
        self.ready.wait()
        return self.index.partial_search(words)


def filename2words(fname):
    """Transforms a filename in the title and words."""
    if fname.endswith(".html"):
        fname = fname[:-5]
    x = normalize_words(fname)
    p = x.split("_")
    t = " ".join(p)
    return p, t


def generate_from_html(dirbase, verbose):
    """Creates the index. used to create new versions of cdpedia."""
    # This isn't needed on the final user, so it is imported here
    from src.preprocessing import preprocess

    # make redirections
    redirs = {}
    for line in open(config.LOG_REDIRECTS, "rt", encoding="utf-8"):
        orig, dest = line.strip().split(config.SEPARADOR_COLUMNAS)

        # in the original article, the title is missing
        # so we use the words founded in the filename
        # it isn't the optimal solution, but works
        words, title = filename2words(orig)
        redirs.setdefault(dest, []).append((words, title))

    top_pages = preprocess.pages_selector.top_pages

    titles_texts = {}
    with open(config.LOG_TITLES, "rt", encoding='utf8') as fh:
        for line in fh:
            arch, title, encoded_primtext = line.strip().split(config.SEPARADOR_COLUMNAS)
            primtext = base64.b64decode(encoded_primtext).decode("utf8")
            titles_texts[arch] = (title, primtext)

    def gen():
        for dir3, arch, score in top_pages:
            # auxiliar info
            namhtml = os.path.join(dir3, arch)
            title, primtext = titles_texts[arch]
            logger.info("Adding to index: [%r]  (%r)" % (title, namhtml))

            # give the title's words great score: 50 plus
            # the original score divided by 1000, to tie-break
            ptje = 50 + score // 1000
            words = WORDS.findall(normalize_words(title))
            yield words, ptje, (namhtml, title, True, primtext)

            # pass words to the redirects which points to
            # this html file, using the same score
            if arch in redirs:
                for (words, title) in redirs[arch]:
                    yield words, ptje, (namhtml, title, False, "")

            # FIXME: las siguientes lineas son en caso de que la generación
            # fuese fulltext, pero no lo es (habrá fulltext en algún momento,
            # pero será desde los bloques, no desde el html, pero guardamos
            # esto para luego)
            #
            # # las words del texto importan tanto como las veces que están
            # all_words = {}
            # for word in WORDS.findall(normalize(palabs_texto)):
            #     all_words[word] = all_words.get(pal, 0) + 1
            # for word, cant in all_words.items():
            #     yield word, (namhtml, title, cant)

    # ensures an empty directory
    if os.path.exists(config.DIR_INDICE):
        shutil.rmtree(config.DIR_INDICE)
    os.mkdir(config.DIR_INDICE)

    Index.create(config.DIR_INDICE, gen())
    return len(top_pages)
