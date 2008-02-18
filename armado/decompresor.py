import os
import struct
import cPickle as pickle
from os import path
#from gzip import GzipFile as compressor
from bz2 import BZ2File as compressor

numBloques = 9
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
	f = compressor("salida/bloques/%s.cdp"%bloqName, "rb")
	headerSize = struct.unpack("<l", f.read(4))[0]
	headerBytes = f.read(headerSize)
	header = pickle.loads(headerBytes)
	for name, origin, size in header:
		if name == fileName:
			f.seek(4+headerSize+origin)
			return f.read(size)

if __name__ == "__main__":
	print getArticle("Queso_de_Vidiago_cbab.html")
