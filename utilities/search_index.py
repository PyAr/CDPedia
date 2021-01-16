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
"""Search text into the index from command-line.

By default, it uses ./idx path."""

import os
import sys
import argparse
import timeit
from unittest.mock import MagicMock
sys.path.append(os.path.abspath(os.curdir))

from src.armado.sqlite_index import Index # NOQA import after fixing path
import src.armado.to3dirs    # NOQA import after fixing path

PAGE = 50
mock = MagicMock()
mock.__contains__ = MagicMock(return_value=True)
src.armado.to3dirs.namespaces = mock


def output(*out):
    if args.file:
        with open(args.file, "a") as fn:
            print(*out, file=fn)
    print(*out)


def show_results(result):
    def show_stat(definition, value):
        output("{:>25}:{}".format(definition, value))

    first_res_time = 0
    nro = None
    for nro, (namhtml, title, ptje, redir, primtext) in enumerate(result):
        if nro == 0:
            first_res_time = timeit.default_timer() - initial_time
            show_stat("First Result", first_res_time)
        if args.verbose and nro <= PAGE:
            # pp(row)
            output('{0:2d}){2:8d} "{1:30s}" {3:70s}'.format(
                nro, title, ptje, primtext[:70].replace("\n", " ")))
        if nro == PAGE:
            first_res_time = timeit.default_timer() - initial_time
            show_stat("First %d Result" % PAGE, first_res_time)
    if nro is None:
        output("No results")
        return
    show_stat("Time", timeit.default_timer() - initial_time)
    show_stat("Results", nro + 1)
    return


if __name__ == "__main__":
    help = """Search some words and compare results in different indexes.

    Uses .idx as default path to index."""

    parser = argparse.ArgumentParser(description=help)
    parser.add_argument('keys', metavar='word', type=str, nargs='+',
                        help='strings to search')
    parser.add_argument('-f', '--file', dest='file', help="append to a file")
    parser.add_argument('-p', '--path', dest='path',
                        default="./idx", help="Index's db path")
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        default=False, help="Show detailed results")
    args = parser.parse_args()
    initial_time = timeit.default_timer()
    idx = Index(args.path)
    output(repr(Index), "   keys=", args.keys)
    delta_time = timeit.default_timer() - initial_time
    output("Open Time: ", delta_time * 100)
    initial_time = timeit.default_timer()
    res = idx.partial_search(args.keys)
    show_results(res)
