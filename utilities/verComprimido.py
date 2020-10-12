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

"""
Muestra info del archivo comprimido.
"""

import logging
import operator
import sys
import os

logger = logging.getLogger(__name__)

sys.path.append(os.getcwd())
from src.armado.compresor import Comprimido, BloqueImagenes  # NOQA import after fixing path


def main(fname, a_extraer):
    fsize = os.stat(fname).st_size
    logger.INFO("Mostrando info del archivo %r (tamaño: %d bytes)" % (fname, fsize))
    if fname.endswith('.cdi'):
        c = BloqueImagenes(fname)
    else:
        c = Comprimido(fname)
    logger.INFO("Del header (%d bytes): %d archivos en total" % (c.header_size, len(c.header)))

    # header: dict con k -> filename
    #                  v -> (seek, size) o el nombre del apuntado
    archivos = []
    redirects = 0
    for name, info in c.header.items():
        if isinstance(info, str):
            redirects += 1
        else:
            (seek, size) = info
            archivos.append((name, seek, size))
    logger.INFO("    %d reales   %d redirects" % (len(archivos), redirects))
    archivos.sort(key=operator.itemgetter(1))
    size_archs = archivos[-1][1] + archivos[-1][2]  # del último, posic + largo

    logger.INFO("Overhead header: %.1f%%" % (100 * (4 + c.header_size) / size_archs))
    logger.INFO("Compresión neta: al %.2f%%" % (100 * fsize / size_archs))

    if not a_extraer:
        # mostramos los archivos que hay adentro
        logger.INFO("Archivos:")
        for name, seek, size in archivos:
            logger.INFO("  ", name.encode("utf8"))
    else:
        # extraemos los archivos indicados
        for arch in a_extraer:
            logger.INFO("Extrayendo", arch.encode("utf8"))
            data = c.get_item(arch)
            with open(os.path.basename(arch), "wb") as fdest:
                fdest.write(data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.INFO("Usar:  verComprimido.py <comprimido> [archivo [...]]")
        logger.INFO("           donde el archivo comprimido es un .cdp / .cdi")
        logger.INFO("           opcionalmente, se pueden pasar archivos a extraer")
        sys.exit()

    main(sys.argv[1], sys.argv[2:])
