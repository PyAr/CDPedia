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

"""Library to create and read index."""

import base64
import config
import logging
import os
import re
import shutil
import threading
import urllib.parse
from collections import defaultdict

from .sqlite_index import Index, normalize_words, IndexEntry


logger = logging.getLogger(__name__)


class IndexInterface(threading.Thread):
    """Process the information needed to connect with index.

    In association with every word will be saved

     - link: the path to the file
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
        return self.index.values()

    def get_random(self):
        """Returns a random article."""
        self.ready.wait()
        value = self.index.random()
        return value

    def search(self, words):
        """Search whole words in the index."""
        self.ready.wait()
        return self.index.search(words)


def tokenize(title):
    """Create list of tokens from given title.

    First that title is normalized, and then is splitted by the following chars (effectively
    removing them):
        - space
        - underscore
        - open and close parentheses
    """
    normalized = normalize_words(title)
    cleaned = re.sub(r'[_\(\)]', ' ', normalized)
    return cleaned.split()


def generate_from_html(dirbase, verbose):
    """Creates the index. used to create new versions of cdpedia."""
    # This isn't needed on the final user, so it is imported here
    from src.preprocessing import preprocess

    # make redirections
    # use a set to avoid duplicated titles after normalization
    redirs = defaultdict(set)
    for line in open(config.LOG_REDIRECTS, "rt", encoding="utf-8"):
        redir_article, orig_article = line.strip().split(config.SEPARADOR_COLUMNAS)
        words = tokenize(redir_article)
        redirs[orig_article].add(tuple(words))

    top_pages = preprocess.pages_selector.top_pages

    titles_texts = {}
    with open(config.LOG_TITLES, "rt", encoding='utf8') as fh:
        for line in fh:
            arch, title, encoded_primtext = line.strip().split(config.SEPARADOR_COLUMNAS)
            primtext = base64.b64decode(encoded_primtext).decode("utf8")
            titles_texts[arch] = (title, primtext)
    already_seen = set()

    def check_already_seen(data):
        """Check for duplicated index entries. Crash if founded."""
        if data in already_seen:
            raise KeyError("Duplicated document in: {}".format(data))
        already_seen.add(data)

    def gen():
        for dir3, arch, pagerank in top_pages:
            # auxiliar info
            link = os.path.join(dir3, arch)
            title, description = titles_texts[arch]
            logger.debug("Adding to index: [%r]  (%r)", title, link)

            # give the title's words great score: 50 plus
            # the original score divided by 1000, to tie-break
            score = 50 + pagerank // 1000
            data = IndexEntry(
                link=link,
                title=title,
                score=score,
                rtype=IndexEntry.TYPE_ORIG_ARTICLE,
                description=description)
            orig_words = tuple(tokenize(title))
            check_already_seen(data)
            yield orig_words, score, data

            # pass words to the redirects which points to
            # this html file, using the same score
            arch_orig = urllib.parse.unquote(arch)  # special filesystem chars
            if arch_orig in redirs:
                redirs[arch_orig].discard(orig_words)
                for redir_words in redirs[arch_orig]:
                    data = IndexEntry(
                        link=link,
                        title=title,
                        subtitle=' '.join(redir_words),
                        score=score,
                        rtype=IndexEntry.TYPE_REDIRECT)
                    check_already_seen(data)
                    yield redir_words, score, data

    # ensures an empty directory
    if os.path.exists(config.DIR_INDICE):
        shutil.rmtree(config.DIR_INDICE)
    os.mkdir(config.DIR_INDICE)

    Index.create(config.DIR_INDICE, gen())
    logger.info("Index created at %s", config.DIR_INDICE)
    return len(top_pages)
