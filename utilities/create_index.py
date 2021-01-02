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
from src.armado.sqlite_index import Index as IndexSQL  # NOQA import after fixing path
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


def generate_from_html(verbose=True):
    """Creates the index. used to create new versions of cdpedia."""
    # make redirections
    with PATH_TEMP.joinpath("redirects.txt").open("rt", encoding='utf8') as fh:
        redirs = defaultdict(set)
        for line in fh:
            orig, dest = line.strip().split(config.SEPARADOR_COLUMNAS, 1)

            # in the original article, the title is missing
            # so we use the words founded in the filename
            # it isn't the optimal solution, but works
            words, title = filename2words(orig)
            try:
                redirs[dest].add(tuple(words))
            except Exception as e:
                print("ERror:", e, line, type(dest), type(words))
    print("Len redirs", len(redirs))

    top_pages = calculate()
    already_seen = set()
    titles_texts = {}
    with PATH_TEMP.joinpath("titles.txt").open("rt", encoding='utf8') as fh:
        for line in fh:
            arch, title, encoded_primtext = line.strip().split(config.SEPARADOR_COLUMNAS)
            primtext = base64.b64decode(encoded_primtext).decode("utf8")
            titles_texts[arch] = (title, primtext)
    print("Len titles", len(titles_texts))

    def check_already_seen(data):
        """Check for duplicated index entries. Crash if founded."""
        if data in already_seen:
            raise KeyError("Duplicated document in: {}".format(data))
        already_seen.add(data)

    def gen():
        """Source generator to SQLite index."""
        for dir3, arch, score in top_pages:
            # auxiliar info
            namhtml = os.path.join(dir3, arch)
            title, primtext = titles_texts[arch]
            logger.debug("Adding to index: [%r]  (%r)" % (title, namhtml))

            # give the title's words great score: 50 plus
            # the original score divided by 1000, to tie-break
            ptje = 50 + score // 1000
            data = (namhtml, title, ptje, True, primtext)
            if not title:
                continue
            check_already_seen(data)
            words = WORDS.findall(normalize_words(title))
            yield words, ptje, data
            # pass words to the redirects which points to
            # this html file, using the same score
            arch_orig = urllib.parse.unquote(arch)
            if arch_orig in redirs:
                ptje = score // 6000
                for words in redirs[arch_orig]:
                    # the title is missing in the original article so we use the words found in
                    # the filename (it isn't the optimal solution, but works)
                    title = " ".join(words)
                    if not title:
                        continue
                    data = (namhtml, title, ptje, False, "")
                    check_already_seen(data)
                    yield list(words), ptje, data

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

    n_pag, gen = generate_from_html()
    idx = IndexSQL.create(str(PATH_IDX), gen())
