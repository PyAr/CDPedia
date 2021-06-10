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

"""Show info of the compressed file."""

from __future__ import division, with_statement, print_function

import operator
import sys
import os
sys.path.append(os.getcwd())
from src.armado.compresor import Comprimido, BloqueImagenes  # NOQA import after fixing path


def main(fname, a_extraer):
    fsize = os.stat(fname).st_size
    print("Showing file info %r (size: %d bytes)" % (fname, fsize))
    if fname.endswith('.cdi'):
        c = BloqueImagenes(fname)
    else:
        c = Comprimido(fname)
    print("From the header (%d bytes): %d files in total" % (c.header_size, len(c.header)))

    # header: dict with k -> filename
    #                  v -> (seek, size) or the name of the target
    archivos = []
    redirects = 0
    for name, info in c.header.items():
        if isinstance(info, str):
            redirects += 1
        else:
            (seek, size) = info
            archivos.append((name, seek, size))
    print("    %d reales   %d redirects" % (len(archivos), redirects))
    archivos.sort(key=operator.itemgetter(1))
    size_archs = archivos[-1][1] + archivos[-1][2]  # del último, posic + largo

    print("Overhead header: %.1f%%" % (100 * (4 + c.header_size) / size_archs))
    print("Net compression: at %.2f%%" % (100 * fsize / size_archs))

    if not a_extraer:
        # showing the files inside
        print("Files:")
        for name, seek, size in archivos:
            print("  ", name.encode("utf8"))
    else:
        # extract the indicated files
        for arch in a_extraer:
            print("Extracting", arch.encode("utf8"))
            data = c.get_item(arch)
            with open(os.path.basename(arch), "wb") as fdest:
                fdest.write(data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Use:  verComprimido.py <compressed> [file [...]]")
        print("           where the compressed file is a .cdp / .cdi")
        print("           optionally, files to extract can be indicated")
        sys.exit()

    main(sys.argv[1], sys.argv[2:])
