# -*- coding: utf-8 -*-

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

from __future__ import print_function

import sys
import optparse
import os

sys.path.append(os.getcwd())
from src.armado.compresor import ArticleManager, ImageManager  # NOQA import after fixing path


def main(manager, nom_item, verbose):
    info = manager.get_item(nom_item)
    if info is None:
        print("Item not found")
    else:
        print("Returned item length", len(info))
        if verbose:
            print("Article:\n", repr(info))


if __name__ == "__main__":
    msg = u"""
  buscarEnBloque.py [-v] [-i] item_name
"""

    parser = optparse.OptionParser()
    parser.set_usage(msg)
    parser.add_option(
        "-v", "--verbose", action="store_true", dest="verbose",
        help="shows info of what it is doing")

    parser.add_option(
        "-i", "--image", action="store_true", dest="image",
        help=u"search in images (search for articles by default)")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        exit()

    nom_item = args[0].decode("utf8")
    verbose = bool(options.verbose)
    if options.image:
        manager = ImageManager(verbose=verbose)
    else:
        manager = ArticleManager(verbose=verbose)

    main(manager, nom_item, verbose)
