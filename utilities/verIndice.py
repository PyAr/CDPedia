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

"""Show index info."""

from __future__ import print_function

import sys
import os
sys.path.append(os.path.abspath("."))

from src.armado.cdpindex import IndexInterface  # NOQA import after fixing the path


def main(direct, words):
    index = IndexInterface(direct)
    index.run()
    index.ready.wait()

    if not words:
        for word, data in index.listar():
            print("%s: %s" % (word.encode("utf8"), data))
    else:
        encontrado = index.search(" ".join(words))
        for it in encontrado:
            print(it)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Use:  verIndice.py <index_dir> [word [...]]")
        print("           index_dir is the directory where is the index")
        print("           optional words are searched in the index")
        sys.exit()

    base = sys.argv[1]
    words = [x.decode("utf8") for x in sys.argv[2:]]
    main(base, words)
