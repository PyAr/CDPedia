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

import argparse
import pathlib
import base64
import logging
import operator
import re
import os
import sys
from logging.handlers import RotatingFileHandler
sys.path.append(os.path.abspath(os.curdir))

import config   # NOQA import after fixing path
from src.armado import to3dirs  # NOQA import after fixing path
from src.armado.sqlite_index import Index as IndexSQL  # NOQA import after fixing path
from src.armado.compressed_index import Index as IndexComp  # NOQA import after fixing path
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
            dir3, fname = to3dirs.get_path_file(page)
            all_pages.append((dir3, fname, int(score)))

    # order by score, and get top N
    all_pages.sort(key=operator.itemgetter(2), reverse=True)
    return all_pages


def generate_from_html(verbose=True):
    """Creates the index. used to create new versions of cdpedia."""
    # make redirections
    redirs = {}
    with PATH_TEMP.joinpath("redirects.txt").open("rt", encoding='utf8') as fh:
        for line in fh:
            orig, dest = line.strip().split(config.SEPARADOR_COLUMNAS)

            # in the original article, the title is missing
            # so we use the words founded in the filename
            # it isn't the optimal solution, but works
            words, title = filename2words(orig)
            redirs.setdefault(dest, []).append((words, title))

    top_pages = calculate()

    titles_texts = {}
    with PATH_TEMP.joinpath("titles.txt").open("rt", encoding='utf8') as fh:
        for line in fh:
            arch, title, encoded_primtext = line.strip().split(config.SEPARADOR_COLUMNAS)
            primtext = base64.b64decode(encoded_primtext).decode("utf8")
            titles_texts[arch] = (title, primtext)

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
            words = list(WORDS.findall(normalize_words(title)))
            yield words, ptje, (namhtml, title, True, primtext)
            # pass words to the redirects which points to
            # this html file, using the same score
            if arch in redirs:
                for (words, title) in redirs[arch]:
                    yield words, ptje, (namhtml, title, False, "")

    return len(top_pages), gen


def ptjes(source):
    """Show ptjes from source."""
    ptjes = {}
    for words, ptje, (namhtml, title, redir, primtext) in source:
        k = ptje // 1000
        ptjes[k] = ptjes.get(k, 0) + 1
    print(ptjes)


def comp(source):
    """Compares title vs generated html path."""
    n = 0
    r = 0
    rr = 0
    for words, ptje, (namhtml, title, ppal, primtext) in source:
        # auxiliar info
        tt = title.replace(" ", "_")
        tt = tt[0].upper() + tt[1:]
        dir3, arch = to3dirs.get_path_file(tt)
        expected = os.path.join(dir3, arch)

        if not ppal:
            rr += 1
        if namhtml != expected:
            if ppal:
                n += 1
                print("-->", namhtml, "\n  `", expected)
            else:
                r += 1
    print("No armables::", n, "   Redirs diferentes::", r, "  Redirs::", rr)


if __name__ == "__main__":
    # main()
    help = """Creates index files.

    Default path is '{}' for index files,
    and '{}' for the scrapped files to index.""".format(PATH_IDX, PATH_TEMP)

    parser = argparse.ArgumentParser(description=help)
    parser.add_argument('-c', '--comp', dest='indexes', action='append_const',
                        const=IndexComp, help="Construct compressed index")
    parser.add_argument('-s', '--sql', dest='indexes', action='append_const',
                        const=IndexSQL, help="Construct sqlite index")
    args = parser.parse_args()
    if not args.indexes:
        print("No index selected!")
        sys.exit(1)
    if PATH_IDX.exists():
        if IndexSQL in args.indexes:
            sqlitepath = PATH_IDX.joinpath("index.sqlite")
            if sqlitepath.exists():
                sqlitepath.unlink()
                print("Database index %s was removed" % sqlitepath)
        if IndexComp in args.indexes:
            for file in PATH_IDX.glob("comp*"):
                file.unlink()
                print("Database index %s was removed" % file)
    else:
        PATH_IDX.mkdir()

    n_pag, gen = generate_from_html()
    if IndexSQL in args.indexes:
        idx = IndexSQL.create(str(PATH_IDX), gen())
    if IndexComp in args.indexes:
        idx = IndexComp.create(str(PATH_IDX), gen())
