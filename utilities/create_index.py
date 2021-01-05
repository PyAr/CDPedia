# -*- encoding: utf8 -*-

# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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

import pathlib
import base64
import logging
import operator
import re
import os
import sys
import urllib.parse
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock
sys.path.append(os.path.abspath(os.curdir))

import config   # NOQA import after fixing path
import src.armado.to3dirs  # NOQA import after fixing path
from src.armado.sqlite_index import Index # NOQA import after fixing path
from src.armado.cdpindex import filename2words, normalize_words  # NOQA import after fixing path

logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter("%(asctime)s  %(name)-20s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("cdpetron.log")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger = logging.getLogger("index")

mock = MagicMock()
mock.__contains__ = MagicMock(return_value=True)
src.armado.to3dirs.namespaces = mock
WORDS = re.compile(r"\w+", re.UNICODE)
PATH_TEMP = pathlib.Path("./temp")
PATH_IDX = pathlib.Path("./idx")
config.LOG_REDIRECTS = PATH_TEMP / "redirects.txt"
config.LOG_TITLES = PATH_TEMP / "titles.txt"


def calculate():
    """Calculate the HTMLs with more score and store both lists."""
    all_pages = []
    colsep = config.SEPARADOR_COLUMNAS
    with PATH_TEMP.joinpath("page_scores_final.txt").open("rt", encoding='utf8') as fh:

        for line in fh:
            page, score = line.strip().split(colsep)
            dir3, fname = src.armado.to3dirs.get_path_file(page)
            all_pages.append((dir3, fname, int(score)))

    # order by score, and get top N
    all_pages.sort(key=operator.itemgetter(2), reverse=True)
    print("Len all_pages", len(all_pages))
    return all_pages


def tokenize_title(title):
    """Create list of tokens from given title."""
    title_norm = normalize_words(title)
    # strip parenthesis from words, for titles like 'Grañón (La Rioja)'
    words = set(w.strip('()') for w in title_norm.split())
    words.update(WORDS.findall(title_norm))
    return words


def generate_from_html(dirbase, verbose):
    """Creates the index. used to create new versions of cdpedia."""
    # make redirections
    # use a set to avoid duplicated titles after normalization
    redirs = defaultdict(set)
    for line in open(config.LOG_REDIRECTS, "rt", encoding="utf-8"):
        orig, dest = line.strip().split(config.SEPARADOR_COLUMNAS)

        # in the original article, the title is missing
        # so we use the words founded in the filename
        # it isn't the optimal solution, but works
        words, title = filename2words(orig)
        redirs[dest].add((tuple(words), title))
    print("Len redirs", len(redirs))

    top_pages = calculate()

    titles_texts = {}
    with open(config.LOG_TITLES, "rt", encoding='utf8') as fh:
        for line in fh:
            arch, title, encoded_primtext = line.strip().split(config.SEPARADOR_COLUMNAS)
            primtext = base64.b64decode(encoded_primtext).decode("utf8")
            titles_texts[arch] = (title, primtext)
    print("Len titles", len(titles_texts))
    already_seen = set()

    def check_already_seen(data):
        """Check for duplicated index entries. Crash if founded."""
        if data in already_seen:
            # raise KeyError("Duplicated document in: {}".format(data))
            print("KeyError Duplicated document in: {}".format(data))
        already_seen.add(data)

    def gen():
        for dir3, arch, score in top_pages:
            # auxiliar info
            namhtml = os.path.join(dir3, arch)
            title, primtext = titles_texts[arch]
            logger.debug("Adding to index: [%r]  (%r)" % (title, namhtml))

            # give the title's words great score: 50 plus
            # the original score divided by 1000, to tie-break
            ptje = 50 + score // 1000
            data = (namhtml, title, ptje, True, primtext)
            check_already_seen(data)
            words = tokenize_title(title)
            yield words, ptje, data
            word_set = set(words)

            # pass words to the redirects which points to
            # this html file, using the same score
            arch_orig = urllib.parse.unquote(arch)  # special filesystem chars
            if arch_orig in redirs:
                ptje = score // 8000
                for (words, title) in redirs[arch_orig]:
                    if not word_set.issuperset(set(words)):
                        data = (namhtml, title, ptje, False, "")
                        check_already_seen(data)
                        yield list(words), ptje, data
                    else:
                        logger.info("Ommited '{}', is subset of '{}'".format(
                            ' '.join(words), ' '.join(word_set)))
    return len(top_pages), gen


if __name__ == "__main__":
    # main()
    help = """Creates index files.

    Default path is '{}' for index files,
    and '{}' for the scrapped files to index.""".format(PATH_IDX, PATH_TEMP)
    print(help)
    if PATH_IDX.exists():
        sqlitepath = PATH_IDX.joinpath("index.sqlite")
        if sqlitepath.exists():
            sqlitepath.unlink()
            print("Database index %s was removed" % sqlitepath)
    else:
        PATH_IDX.mkdir()

    if PATH_TEMP.exists():
        for filename in ["titles.txt", "page_scores_final.txt", "redirects.txt"]:
            if not PATH_TEMP.joinpath(filename).exists():
                raise FileNotFoundError("The file {} is needed".format(
                    str(PATH_TEMP.joinpath(filename))))

    n_pag, gen = generate_from_html(PATH_TEMP, verbose=True)
    idx = Index.create(str(PATH_IDX), gen())
