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
from src.armado.sqlite_index import Index as IndexComp # NOQA import after fixing path
# from src.armado.compressed_index import Index as IndexComp # NOQA import after fixing path

PAGE = 40


def show_results(result, verbose):
    res = []
    stats = {}
    first_res_time = 0
    for row in result:
        res.append(row)
        if args.verbose:
            # pp(row)
            print(len(res), row[1])
        if len(res) == 1:
            first_res_time = timeit.default_timer() - initial_time
            stats["First Result"] = first_res_time
        if len(res) == PAGE:
            first_res_time = timeit.default_timer() - initial_time
            stats["First %d Result" % PAGE] = first_res_time
    stats["Time"] = timeit.default_timer() - initial_time
    stats["Results"] = len(res)
    for k, v in stats.items():
        print("{:>25}:{}".format(k, v))
    return [tuple(r[0:2]) for r in res]


def show(title, data, other):
    n = 0
    p = []
    for item in data:
        if item not in other:
            print("     ", item)
            n += 1
        else:
            pos = other.index(item)
            if pos in p:
                print("repetido:", item)
            p.append(other.index(item))
    print(title, " Total:", n, "   data:", len(data), " other:", len(other))
    print("-" * 40)
    return n


if __name__ == "__main__":
    PATH_IDX = "./idx"
    help = """Search some words and compare results in different indexes.

    Uses {} as path to index.""".format(PATH_IDX)

    parser = argparse.ArgumentParser(description=help)
    parser.add_argument('keys', metavar='word', type=str, nargs='+',
                        help='strings to search')
    parser.add_argument('-c', '--comp', dest='indexes', action='append_const',
                        const=IndexComp, help="use compressed index")
    parser.add_argument('-s', '--sql', dest='indexes', action='append_const',
                        const=IndexSQL, help="use sqlite index")
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        default=False, help="Show detailed results")
    parser.add_argument('-w', '--word', dest='complete', action='store_true',
                        default=False, help="complete word search")
    parser.add_argument('-p', '--partial', dest='partial', action='store_true',
                        default=False, help="partial word search")
    parser.add_argument('-d', '--difference', dest='diff', action='store_true',
                        default=False, help="differences in search's results")
    args = parser.parse_args()
    if not args.indexes:
        args.indexes = [IndexSQL, IndexComp]
    if not args.complete and not args.partial:
        args.complete = True
        args.partial = True
    res_part = [0] * 2
    res_comp = [0] * 2
    # print(args)
    args.indexes = [IndexSQL]
    for nro, Index in enumerate(args.indexes):
        initial_time = timeit.default_timer()
        idx = Index(PATH_IDX)
        print(repr(Index))
        delta_time = timeit.default_timer() - initial_time
        print("Open Time: ", delta_time * 100)
        if args.complete:
            initial_time = timeit.default_timer()
            res = idx.search(args.keys)
            res_comp[nro] = show_results(res, args.verbose)
        """
        if args.partial:
            initial_time = timeit.default_timer()
            res = idx.partial_search(args.keys)
            res_part[nro] = show_results(res, args.verbose)
        """

    if args.diff:
        show("Complete word: in sql not in comp", res_comp[0], res_comp[1])
        show("Complete word: in comp not in sql", res_comp[1], res_comp[0])
        show("Partial word: in sql not in comp", res_part[0], res_part[1])
        show("Partial word: in comp not in sql", res_part[1], res_part[0])
