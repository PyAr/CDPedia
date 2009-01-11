# -*- encoding: utf8 -*-

"""
Muestra info del archivo comprimido.
"""

from __future__ import division
from __future__ import with_statement

import struct
import cPickle as pickle
from bz2 import BZ2File as CompressedFile
import operator
import sys
import os

def main(fname, a_extraer):
    fsize = os.stat(fname).st_size
    print "Mostrando info del archivo %r (tamaño: %d bytes)" % (fname, fsize)

    fh = CompressedFile(fname, "rb")
    header_size = struct.unpack("<l", fh.read(4))[0]
    header_bytes = fh.read(header_size)
    header = pickle.loads(header_bytes)
    print "Del header (%d bytes): %d archivos en total" % (
                                                    header_size, len(header))

    # header: dict con k -> filename
    #                  v -> (seek, size) o el nombre del apuntado
    archivos = []
    redirects = 0
    for name, info in header.items():
        if isinstance(info, basestring):
            redirects += 1
        else:
            (seek, size) = info
            archivos.append((name, seek, size))
    print "    %d reales   %d redirects" % (len(archivos), redirects)
    archivos.sort(key=operator.itemgetter(1))
    size_archs = archivos[-1][1] + archivos[-1][2] # del último, posic + largo

    print "Overhead header: %.1f%%" % (100 * (4 + header_size) / size_archs)
    print "Compresión neta: al %.2f%%" % (100 * fsize / size_archs)

    if not a_extraer:
        # mostramos los archivos que hay adentro
        print "Archivos:"
        for name, seek, size in archivos:
            print "  ", name
    else:
        # extraemos los archivos indicados
        for arch in a_extraer:
            print "Extrayendo", arch
            info = header[arch]
            while isinstance(info, basestring):
                print "  redirigido a", info
                arch = info
                info = header[arch]
            (seek, size) = info
            print "    seek %d   size %d" % (seek, size)
            fh.seek(4 + header_size + seek)
            data = fh.read(size)
            print "    extrayendo", arch
            with open(arch, "wb") as fdest:
                fdest.write(data)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usar:  verComprimido.py <comprimido> [archivo [...]]"
        print "           donde el archivo comprimido es un .odp"
        print "           opcionalmente, se pueden pasar archivos a extraer"
        sys.exit()

    main(sys.argv[1], sys.argv[2:])
