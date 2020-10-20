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

import os
import sys
import argparse
import timeit
sys.path.append(os.path.abspath(os.curdir))

from src.armado.sqlite_index import Index as IndexSQL # NOQA import after fixing path
#from src.armado.sqlite_index import Index as IndexComp # NOQA import after fixing path
from src.armado.compressed_index import Index as IndexComp # NOQA import after fixing path

PAGE = 3004

def output(*out):
    if args.file:
        with open(args.file, "a") as fn:
            print(*out, file=fn)
    print(*out)


def show_results(result, verbose):
    def show_stat(definition, value):
        output("{:>25}:{}".format(definition, value))

    res = []
    first_res_time = 0
    for row in result:
        res.append(row)
        if len(res) == 1:
            first_res_time = timeit.default_timer() - initial_time
            print(row)
            show_stat("First Result", first_res_time)
        if args.verbose and len(res) <= PAGE:
            # pp(row)
            output('{0:2d}){2:8d} "{1:30s}"{4} {3:70s}'.format(
                len(res), row[1], row[-2], row[-3][:70].replace("\n", " "), row[-1]))
        if len(res) == PAGE:
            first_res_time = timeit.default_timer() - initial_time
            show_stat("First %d Result" % PAGE, first_res_time)
    show_stat("Time", timeit.default_timer() - initial_time)
    show_stat("Results", len(res))
    return [tuple(r[0:2]) for r in res]


def show(title, data, other):
    n = 0
    p = []
    for item in data:
        if item not in other:
            output("     ", item)
            n += 1
        else:
            pos = other.index(item)
            if pos in p:
                output("repetido:", item)
            p.append(other.index(item))
    output(title, " Total:", n, "   data:", len(data), " other:", len(other))
    output("-" * 40)
    return n


if __name__ == "__main__":
    help = """Search some words and compare results in different indexes.

    Uses .idx as path to index."""

    parser = argparse.ArgumentParser(description=help)
    parser.add_argument('keys', metavar='word', type=str, nargs='+',
                        help='strings to search')
    parser.add_argument('-f', '--file', dest='file', help="append to a file")
    parser.add_argument('-c', '--comp', dest='indexes', action='append_const',
                        const=IndexComp, help="use compressed index")
    parser.add_argument('-s', '--sql', dest='indexes', action='append_const',
                        const=IndexSQL, help="use sqlite index")
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        default=False, help="Show detailed results")
    parser.add_argument('-d', '--difference', dest='diff', action='store_true',
                        default=False, help="differences in search's results")
    args = parser.parse_args()
    if not args.indexes:
        args.indexes = [IndexSQL, IndexComp]
    path = {IndexSQL: "./idx", IndexComp: "./idx/old"}
    res_part = [0] * 2
    res_comp = [0] * 2
    # args.indexes = [IndexSQL]
    for nro, Index in enumerate(args.indexes):
        initial_time = timeit.default_timer()
        idx = Index(path[Index])
        output(repr(Index), "   keys=", args.keys)
        delta_time = timeit.default_timer() - initial_time
        output("Open Time: ", delta_time * 100)
        initial_time = timeit.default_timer()
        res = idx.search(args.keys)
        res_comp[nro] = show_results(res, args.verbose)

    if args.diff:
        show("Complete word: in sql not in comp", res_comp[0], res_comp[1])
        show("Complete word: in comp not in sql", res_comp[1], res_comp[0])
        show("Partial word: in sql not in comp", res_part[0], res_part[1])
        show("Partial word: in comp not in sql", res_part[1], res_part[0])
