import os
import struct
import cPickle as pickle
from os import path
#from gzip import GzipFile as CompressedFile
from bz2 import BZ2File as CompressedFile
import types

DIR_BLOQUES="bloques"
ARTICLES_PER_BLOCK=1000

"""
Formato del bloque:

4 bytes: Longitud del header
Header: pickle de una lista de tuplas (nombre_articulo, origen, tamanio)
    (el origen es 0 despues del header)

Articulos, uno detras del otro
"""
numBloques = None

def getArticle(fileName):
    global numBloques
    if numBloques is None:
        numBloques = len([n for n in os.listdir(DIR_BLOQUES) if n[-4:]==".cdp"])
    bloqNum = hash(fileName)%numBloques
    bloqName = "%08x"%bloqNum
    f = CompressedFile((DIR_BLOQUES+"/%s.cdp")%bloqName, "rb")
    headerSize = struct.unpack("<l", f.read(4))[0]
    headerBytes = f.read(headerSize)
    header = pickle.loads(headerBytes)
    data= header[fileName]
    if type (data) in types.StringTypes:
        fileName= data
        data= getArticle (fileName)
    else:
        (seek, size)= data
        f.seek(4+headerSize+seek)
        data= f.read(size)
    return data

if __name__ == "__main__":
    print repr(getArticle(u"Zumaia.html".encode("utf-8")))
    print repr(getArticle(u'Discusi\xf3n~Zurdo_ce85.html'.encode("utf-8")))

# end
