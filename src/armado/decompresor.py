# -*- coding: utf8 -*-

"""
Formato del bloque:

    4 bytes: Longitud del header

    Header: pickle de un diccionario:
             clave -> nombre del archivo original
             valor -> si es string, el nombre del archivo real (es un redirect)
                      si no es string, es una tupla (posición, tamaño)

    Artículos, uno detrás del otro (el origen es 0 despues del header)
"""

import os
import struct
import cPickle as pickle
from os import path
from bz2 import BZ2File as CompressedFile

import config

numBloques = None

def getArticle(fileName):
    global numBloques
    if numBloques is None:
        numBloques = len([n for n in os.listdir(config.DIR_BLOQUES) if n[-4:]==".cdp"])
    bloqNum = hash(fileName)%numBloques
    bloqName = "%08x"%bloqNum
    f = CompressedFile((config.DIR_BLOQUES+"/%s.cdp")%bloqName, "rb")
    headerSize = struct.unpack("<l", f.read(4))[0]
    headerBytes = f.read(headerSize)
    header = pickle.loads(headerBytes)

    if fileName not in header:
        return None

    info = header[fileName]
    if isinstance(info, basestring):
        # info es un link a lo real, hacemos recursivo
        data = getArticle(info)
    else:
        (seek, size) = info
        f.seek(4 + headerSize + seek)
        data = f.read(size)
    return data

if __name__ == "__main__":
    # esto es para pruebas
    print repr(getArticle(u"Zumaia.html".encode("utf-8")))
    print repr(getArticle(u'Discusi\xf3n~Zurdo_ce85.html'.encode("utf-8")))
