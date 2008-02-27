# -- encoding: latin1 --
import sys
import os
from os import path
import shutil

# trabajar desde el directorio de la cdpedia
basedir = path.abspath(path.dirname(sys.argv[0]))
os.chdir(basedir)
# agregar modulos al path de python
sys.path.extend( path.join(basedir, n) for n in "src/armado src/preproceso".split() )
import config


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
    import preprocesar
    preprocesar.run()

def borrarBloques(dest):
    """borrar el directorio de bloques existente y volver a crearlo vacío"""
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)

def generarBloques(dest):
    if not path.exists(dest):
        os.makedirs(dest)
    import compresor
    compresor.generar()

def armarEjecutable():
    pass

def armarIso(dest):
    pass

copiarAssets("salida/assets")
copiarSources("salida/source")
if sys.platform == "win32":
    armarEjecutable()

preprocesar()
borrarBloques("salida/bloques")
generarBloques("salida/bloques")
armarIso("cdpedia.iso")

print "presione enter"
a=raw_input()
