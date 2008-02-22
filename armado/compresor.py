import os
import struct
import cPickle as pickle
from os import path
#from gzip import GzipFile as compressor
from bz2 import BZ2File as compressor

from decompresor import ARTICLES_PER_BLOCK
PATH = "procesado/es"

"""
Formato del bloque:

4 bytes: Longitud del header
Header: pickle de una lista de tuplas (nombre_articulo, origen, tamanio)
    (el origen es 0 despues del header)

Articulos, uno detras del otro
"""

def recortar(seudopath):
    return path.basename(seudopath)

def generar():
    # recorrer todos los nombres de articulos, y ordenarlos en un dict por su numero de bloque, segun el hash
    fileNames = []
    for root, dirs, files in os.walk(PATH):
        for fileName in files:
            fileNames.append( (root, fileName) )
            if len(fileNames)%10000 == 0:
                print "encontrados %d articulos" % len(fileNames)

    print "procesando", len(fileNames), "articulos"
    numBloques= len(fileNames) / ARTICLES_PER_BLOCK
    bloques = {}
    for root, fileName in fileNames:
        bloqNum = hash(fileName)%numBloques
        if bloqNum not in bloques:
            bloques[bloqNum] = []
        bloques[bloqNum].append((root,fileName))
    
    # armo el diccionario de redirects
    redirects = dict( (n,{}) for n in range(numBloques) )
    for linea in open("redirects.txt"):
        desde, hasta = linea.split()
        desde = recortar(desde)
        hasta = recortar(hasta)
        bloqNum = hash(desde)%numBloques
        redirects[bloqNum][desde]=hasta

    # recorrer el dict de bloques, juntando cada uno
    for bloqNum, fileNames in bloques.items():

        # armo el header, con un ejemplo de redirect
        header= redirects[bloqNum]
        seek = 0
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
            size = path.getsize(fullName)
            header[fileName]= (seek, size)
            seek += size
        headerBytes = pickle.dumps(header)
        
        print "procesando bloque", bloqNum, "de", numBloques, "(header size=%d)"%len(headerBytes)
        # abro el archivo a comprimir
        bloqName = "%08x"%bloqNum
        f = compressor("salida/bloques/%s.cdp"%bloqName, "wb")

        # grabo la longitud del header, y el header
        f.write( struct.pack("<l", len(headerBytes) ) )
        f.write( headerBytes )
        
        # grabo cada uno de los articulos
        for root, fileName in fileNames:
            fullName = path.join(root, fileName)
            f.write(open( fullName ).read())

        f.close()

if __name__ == "__main__":
    generar()
