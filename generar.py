# -- encoding: latin1 --
import sys
import shutil
import os
from os import path
import config

sys.path.append( "src/armado src/preproceso".split() )

def copiarAssets(dest):
    """copiar los assets, si no estaban"""
    if not path.exists(dest):
        os.makedirs(dest)
        for d in ["es/skins", "es/images", "es/raw"]:
            shutil.copytree(d, path.join(dest, path.split(d)[-1]))

def copiarSources(dest):
    """copiar los fuentes"""
    if not path.exists(dest):
        os.makedirs(dest)
    for f in "src/armado/main.py src/armado/server.py src/armado/decompresor.py".split():
        shutil.copy(f, dest)

def preprocesar():
    exec( open("src/preproceso/preprocesar.py") )

def borrarBloques(dest):
    """borrar el directorio de bloques existente y volver a crearlo vacío"""
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)

def generarBloques(dest):
    exec( open("src/armado/compresor.py") )

# trabajar desde el directorio de la cdpedia
os.chdir(path.dirname(sys.argv[0]))

copiarAssets("salida/assets")
copiarSources("salida/source")

preprocesar()
#borrarBloques("salida/bloques")
generarBloques("salida/bloques")

print "presione enter"
a=raw_input()
