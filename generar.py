# -- encoding: utf-8 --

import sys
import os
from os import path
import shutil
import time

import config
from src.preproceso import preprocesar
from src.armado import compresor
from src.armado import cdpindex

def mensaje(texto):
    fh = time.strftime("%Y-%m-%d %H:%M:%S")
    print "%-40s (%s)" % (texto, fh)

def copiarAssets(src_info, dest):
    """Copiar los assets."""
    os.makedirs(dest)
    for d in config.ASSETS:
        src_dir = path.join(src_info, d)
        dst_dir = path.join(dest, d)
        if not os.path.exists(src_dir):
            print "\nERROR: No se encuentra el directorio %r" % src_dir
            print "Este directorio es obligatorio para el procesamiento general"
            sys.exit()
        shutil.copytree(src_dir, dst_dir)

def copiarSources():
    """Copiar los fuentes."""
    orig_src = "src/armado"
    dest_src = path.join(config.DIR_CDBASE, "src")

    # las fuentes
    os.makedirs(dest_src)
    for name in "server.py decompresor.py".split():
        fullname = path.join(orig_src, name)
        shutil.copy(fullname, dest_src)

    # el main va al root
    shutil.copy("main.py", config.DIR_CDBASE)

def armarEjecutable():
    pass

def armarIso(dest):
    os.system("mkisofs -quiet -o " + dest + " -R -J " + config.DIR_CDBASE)

def genera_run_config():
    f = open(path.join(config.DIR_CDBASE, "config.py"), "w")
    f.write('from src import server\n')
    f.write('DIR_BLOQUES = "../bloques"\n')
    f.write('DIR_ASSETS = "assets"\n')
    f.write('ASSETS = %s\n' % config.ASSETS)
    f.close()

def main(src_info):
    mensaje("Comenzando!")

    # limpiamos el directorio temporal
    shutil.rmtree(config.DIR_TEMP, ignore_errors=True)
    os.makedirs(config.DIR_TEMP)

    mensaje("Copiando los assets")
    copiarAssets(src_info, config.DIR_ASSETS)

    mensaje("Copiando las fuentes")
    copiarSources()

    # FIXME: ¿esto al final se hace por afuera?
    if sys.platform == "win32":
        armarEjecutable()

    mensaje("Preprocesando")
    preprocesar.run(src_info)

    mensaje("Generando el índice")
    cdpindex.generar(src_info)

    mensaje("Generando los bloques")
    dest = path.join(config.DIR_BLOQUES)
    os.makedirs(dest)
    compresor.generar()

    mensaje("Generamos la config para runtime")
    genera_run_config()

    mensaje("Armamos el ISO")
    armarIso("cdpedia.iso")

    mensaje("Todo terminado!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usar generar.py <directorio>"
        print "  donde directorio es el lugar donde está la info"
        sys.exit()

    main(sys.argv[1])
