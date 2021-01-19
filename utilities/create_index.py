# Copyright 2021 CDPedistas (see AUTHORS.txt)
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
"""Create index using data in ./temp.

By default, it put it in ./idx path.
"""

import pathlib
import logging
import operator
import re
import os
import sys
from unittest.mock import MagicMock
from logging.handlers import RotatingFileHandler

sys.path.append(os.path.abspath(os.curdir))

import config   # NOQA import after fixing path
from src.armado import to3dirs  # NOQA import after fixing path
from src.armado.sqlite_index import Index as IndexSQL  # NOQA import after fixing path
from src.armado.cdpindex import generate_from_html # NOQA import after fixing path
import src.armado.to3dirs    # NOQA import after fixing path
import src.preprocessing.preprocess    # NOQA import after fixing path

mock = MagicMock()
mock.__contains__ = MagicMock(return_value=True)
src.armado.to3dirs.namespaces = mock

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


class fake_page_selector:
    @property
    def top_pages(self):
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


src.preprocessing.preprocess.pages_selector = fake_page_selector()
config.DIR_INDICE = PATH_IDX


if __name__ == "__main__":
    # main()
    help = """Creates index files.

    Default path is '{}' for index files,
    and '{}' for the scrapped files to index.""".format(PATH_IDX, PATH_TEMP)

    sqlitepath = PATH_IDX.joinpath("index.sqlite")
    if sqlitepath.exists():
        sqlitepath.unlink()
        print("Database index %s was removed" % sqlitepath)
    elif not PATH_IDX.exists():
        PATH_IDX.mkdir()

    n_pag = generate_from_html(PATH_TEMP, verbose=True)
