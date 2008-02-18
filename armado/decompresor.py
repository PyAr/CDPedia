import os
import struct
import cPickle as pickle
from os import path
#from gzip import GzipFile as compressor
from bz2 import BZ2File as compressor
import types

numBloques = 17
from compresor import ARTICLES_PER_BLOCK

"""
Formato del bloque:

4 bytes: Longitud del header
Header: pickle de una lista de tuplas (nombre_articulo, origen, tamanio)
	(el origen es 0 despues del header)

Articulos, uno detras del otro
"""

def getArticle(fileName):
	bloqNum = hash(fileName)%numBloques
	bloqName = "%08x"%bloqNum
        print bloqName
	f = compressor("salida/bloques/%s.cdp"%bloqName, "rb")
	headerSize = struct.unpack("<l", f.read(4))[0]
	headerBytes = f.read(headerSize)
        header = pickle.loads(headerBytes)
        print 
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
	print getArticle("Quintana_y_Congosto_3e17.html")
	print getArticle("a.html")

# end
