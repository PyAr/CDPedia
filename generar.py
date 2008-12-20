# -- encoding: latin1 --
import sys
import os
from os import path
import shutil

# trabajar desde el directorio de la cdpedia
basedir = path.abspath(path.dirname(sys.argv[0]))
os.chdir(basedir)
# agregar modulos al path de python
sys.path.extend( path.join(basedir, n) for n in ". src/armado src/preproceso".split() )
import config
from decompresor import DIR_BLOQUES


def copiarAssets(dest):
    """copiar los assets, si no estaban"""
    print "Copiando los assets"
    if not path.exists(dest):
        os.makedirs(dest)
        for d in ["es/skins", "es/images", "es/raw"]:
            shutil.copytree(d, path.join(dest, path.split(d)[-1]))

def copiarSources(dest):
    """copiar los fuentes"""
    print "Copiando los fuentes"
    if not path.exists(dest):
        os.makedirs(dest)
    for f in "src/armado/main.py src/armado/server.py src/armado/decompresor.py".split():
        shutil.copy(f, dest)

def preprocesar():
    print "Prepocesando"
    if not path.exists(config.DIR_TEMP):
        os.makedirs(config.DIR_TEMP)
    import preprocesar
    preprocesar.run()

def borrarBloques(dest):
    """borrar el directorio de bloques existente y volver a crearlo vacío"""
    print "Limpiando bloques viejos"
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)

def generarBloques(dest):
    print "Generando los bloques"
    if not path.exists(dest):
        os.makedirs(dest)
    import compresor
    compresor.generar()

def armarEjecutable():
    pass

def armarIso(dest):
    print "Armando el ISO"
    os.system("mkisofs -o " + dest + " -R -J " + config.DIR_CDBASE)

copiarAssets(config.DIR_CDBASE + "/" + config.DIR_ASSETS)
copiarSources(config.DIR_CDBASE + "/src")
if sys.platform == "win32":
    armarEjecutable()

preprocesar()
borrarBloques(config.DIR_CDBASE + "/" + DIR_BLOQUES)
generarBloques(config.DIR_CDBASE + "/" + DIR_BLOQUES)
armarIso("cdpedia.iso")
print "Todo terminado!"
