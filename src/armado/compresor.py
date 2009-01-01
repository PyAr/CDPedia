# -*- coding: utf8 -*-

"""
Compresor de los archivos crudos a los archivos de bloques.

Formato del bloque:

4 bytes: Longitud del header
Header: pickle de un diccionario de tuplas {nombre_articulo: (origen, tamanio)}
    (el origen es 0 despues del header)
Articulos, uno detras del otro
"""

from __future__ import division
import os
import codecs
import struct
import cPickle as pickle
from os import path
from bz2 import BZ2File as CompressedFile
import config

def recortar(seudopath):
    return path.basename(seudopath)

def generar():
    # recorrer todos los nombres de articulos, y ordenarlos en un dict por
    # su numero de bloque, segun el hash
    fileNames = []
    print "Buscando los artículos"
    for root, dirs, files in os.walk(unicode(config.DIR_PREPROCESADO)):
        for fileName in files:
            fileNames.append( (root, fileName) )
            if len(fileNames)%10000 == 0:
                print "  encontrados %d artículos" % len(fileNames)

    print "Procesando", len(fileNames), "articulos"
    numBloques= max(len(fileNames) // config.ARTICLES_PER_BLOCK, 1)
    bloques = {}
    for root, fileName in fileNames:
#        print "  archs:", root, fileName
        bloqNum = hash(fileName) % numBloques
        if bloqNum not in bloques:
            bloques[bloqNum] = []
        bloques[bloqNum].append((root,fileName))

    # armo el diccionario de redirects
    redirects = dict( (n,{}) for n in range(numBloques) )
    for linea in codecs.open(config.LOG_REDIRECTS, "r", "utf-8"):
        desde, hasta = linea.split()
        desde = recortar(desde)
        hasta = recortar(hasta)
#        print "  redirs:", desde, hasta
        bloqNum = hash(desde) % numBloques
        redirects[bloqNum][desde] = hasta

    # recorrer el dict de bloques, juntando cada uno
    for bloqNum, fileNames in bloques.items():
        print "Procesando el bloque %d (de %d)" % (bloqNum, numBloques)

        # armo el header con un ejemplo de redirect
        header = redirects[bloqNum]
        seek = 0
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
            size = path.getsize(fullName)
            header[fileName.encode("utf-8")] = (seek, size)
            seek += size
        headerBytes = pickle.dumps(header)
        print "  archivos: %d   seek total: %d   largo header: %d" % (
                                    len(fileNames), seek, len(headerBytes))

        # abro el archivo a comprimir
        nomfile = path.join(config.DIR_BLOQUES, "%08x.cdp" % bloqNum)
        print "  grabando en", nomfile
        f = CompressedFile(nomfile, "wb")

        # grabo la longitud del header, y el header
        f.write( struct.pack("<l", len(headerBytes) ) )
        f.write( headerBytes )

        # grabo cada uno de los articulos
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
            f.write(open( fullName, "rb" ).read())

        f.close()

if __name__ == "__main__":
    generar()
