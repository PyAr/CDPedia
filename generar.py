# -- encoding: utf-8 --

import sys
import os
from os import path
import shutil
import time

### trabajar desde el directorio de la cdpedia
##basedir = path.abspath(path.dirname(sys.argv[0]))
##os.chdir(basedir)
### agregar modulos al path de python
##sys.path.extend( path.join(basedir, n) for n in ". src/armado src/preproceso".split() )

import config
from src.preproceso import preprocesar
from src.armado import compresor
from src.armado.decompresor import DIR_BLOQUES

def mensaje(texto):
    fh = time.strftime("%Y-%m-%d %H:%M:%S")
    print "%-40s (%s)" % (texto, fh)

def copiarAssets(src_info, dest):
    """Copiar los assets."""
    os.makedirs(dest)
    for d in ["skins", "images", "raw"]:
        src_dir = path.join(src_info, d)
        dst_dir = path.join(dest, d)
        if not os.path.exists(src_dir):
            print "\nERROR: No se encuentra el directorio %r" % src_dir
            print "Este directorio es obligatorio para el procesamiento general"
            sys.exit()
        shutil.copytree(src_dir, dst_dir)

def copiarSources(fuente, dest):
    """Copiar los fuentes."""
    os.makedirs(dest)
    for name in "main.py server.py decompresor.py".split():
        fullname = path.join(fuente, name)
        shutil.copy(fullname, dest)

def armarEjecutable():
    pass

def armarIso(dest):
    os.system("mkisofs -o " + dest + " -R -J " + config.DIR_CDBASE)

def main(src_info):
    mensaje("Comenzando!")

    # limpiamos el directorio temporal
    shutil.rmtree(config.DIR_TEMP, ignore_errors=True)
    os.makedirs(config.DIR_TEMP)

    mensaje("Copiando los assets")
    destino = path.join(config.DIR_CDBASE, config.DIR_ASSETS)
    copiarAssets(src_info, destino)

    mensaje("Copiando las fuentes")
    destino = path.join(config.DIR_CDBASE, "src")
    copiarSources("src/armado", destino)

    # FIXME: ¿esto al final se hace por afuera?
    if sys.platform == "win32":
        armarEjecutable()

    mensaje("Preprocesando")
    preprocesar.run(src_info)

    mensaje("Generando los bloques")
    dest = path.join(config.DIR_CDBASE, DIR_BLOQUES)
    os.makedirs(dest)
    compresor.generar()

    mensaje("Armamos el ISO")
    armarIso("cdpedia.iso")

    mensaje("Todo terminado!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usar generar.py <directorio>"
        print "  donde directorio es el lugar donde está la info"
        sys.exit()

    main(sys.argv[1])
