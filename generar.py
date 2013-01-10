# -- encoding: utf-8 --

from __future__ import with_statement

import optparse
import os
import shutil
import subprocess
import sys
import time

from os import path

#Para poder hacer generar.py > log.txt
if sys.stdout.encoding is None:
    reload(sys)
    sys.setdefaultencoding('utf8')

import config
from src.preproceso import preprocesar
from src.armado.compresor import ArticleManager, ImageManager
from src.armado import cdpindex
from src.armado.compressed_index import  NO_ST_MSG
from src.imagenes import extraer, download, reducir, calcular


def make_it_nicer():
    """Make the process nicer at CPU and IO levels."""
    # cpu, simple
    os.nice(19)

    # IO, much more complicated
    pid = os.getpid()
    subprocess.call(["ionice", "-c", "Idle", "-p", str(pid)])


def mensaje(texto):
    fh = time.strftime("%Y-%m-%d %H:%M:%S")
    print "%-40s (%s)" % (texto, fh)


def copy_dir(src_dir, dst_dir):
    '''Copia un directorio recursivamente.

    No se lleva .* (por .svn) ni los .pyc.
    '''
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    for fname in os.listdir(src_dir):
        if fname.startswith("."):
            continue
        if fname.endswith('.pyc'):
            continue
        src_path = path.join(src_dir, fname)
        dst_path = path.join(dst_dir, fname)
        if path.isdir(src_path):
            copy_dir(src_path, dst_path)
        else:
            shutil.copy(src_path, dst_path)

def copiarAssets(src_info, dest):
    """Copiar los assets."""
    if not os.path.exists(dest):
        os.makedirs(dest)

    assets = config.ASSETS
    if config.EDICION_ESPECIAL is not None:
        assets.append(config.EDICION_ESPECIAL)

    for d in assets:
        src_dir = path.join(config.DIR_SOURCE_ASSETS, d)
        dst_dir = path.join(dest, d)
        if not os.path.exists(src_dir):
            print "\nERROR: No se encuentra el directorio %r" % src_dir
            print "Este directorio es obligatorio para el procesamiento general"
            sys.exit()
        copy_dir(src_dir, dst_dir)

    # externos (de nosotros, bah)
    src_dir = "resources/external_assets"
    dst_dir = path.join(dest, "extern")
    copy_dir(src_dir, dst_dir)

    # info general
    src_dir = "resources/general_info"
    copy_dir(src_dir, config.DIR_CDBASE)
    shutil.copy('AUTHORS.txt', os.path.join(config.DIR_CDBASE, 'AUTORES.txt'))

    # institucional
    src_dir = "resources/institucional"
    dst_dir = path.join(dest, "institucional")
    copy_dir(src_dir, dst_dir)

    # compressed assets
    src_dir = "resources"
    for asset in config.COMPRESSED_ASSETS:
        shutil.copy(path.join(src_dir, asset), dest)


def copiarSources():
    """Copiar los fuentes."""
    # el src
    dest_src = path.join(config.DIR_CDBASE, "cdpedia", "src")
    dir_a_cero(dest_src)
    shutil.copy(path.join("src", "__init__.py"), dest_src)
    shutil.copy(path.join("src", "utiles.py"), dest_src)
    copy_dir(path.join("src", "armado"),
             path.join(config.DIR_CDBASE, "cdpedia", "src", "armado"))
    copy_dir(path.join("src", "web"),
             path.join(config.DIR_CDBASE, "cdpedia", "src", "web"))
    copy_dir(path.join("src", "third_party"),
             path.join(config.DIR_CDBASE, "cdpedia", "src", "third_party"))

    # el main va al root
    shutil.copy("cdpedia.py", config.DIR_CDBASE)

    if config.DESTACADOS:
        shutil.copy(config.DESTACADOS,
                    os.path.join(config.DIR_CDBASE, "cdpedia"))


def dir_a_cero(path):
    """Crea un directorio borrando lo viejo si existiera."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def armarIso(dest):
    """Arma el .iso de la CDPedia."""
    os.system("mkisofs -hide-rr-moved -quiet -V CDPedia -volset "
              "CDPedia -o %s -R -J %s" % (dest, config.DIR_CDBASE))


def genera_run_config():
    f = open(path.join(config.DIR_CDBASE, "cdpedia", "config.py"), "w")
    f.write('import os\n\n')
    f.write('VERSION = %s\n' % repr(config.VERSION))
    f.write('SERVER_MODE = %s\n' % config.SERVER_MODE)
    f.write('EDICION_ESPECIAL = %s\n' % repr(config.EDICION_ESPECIAL))
    f.write('HOSTNAME = "%s"\n' % config.HOSTNAME)
    f.write('PORT = %d\n' % config.PORT)
    f.write('INDEX = "%s"\n' % config.INDEX)
    f.write('ASSETS = %s\n' % config.ASSETS)
    f.write('ALL_ASSETS = %s\n' % config.ALL_ASSETS)
    f.write('DESTACADOS = os.path.join("cdpedia", "%s")\n' % config.DESTACADOS)
    f.write('DEBUG_DESTACADOS = %s\n' % repr(config.DEBUG_DESTACADOS))
    f.write('BROWSER_WD_SECONDS = %d\n' % config.BROWSER_WD_SECONDS)
    f.write('SEARCH_RESULTS = %d\n' % config.SEARCH_RESULTS)
    f.write('URL_WIKIPEDIA = "%s"\n' % config.URL_WIKIPEDIA)
    f.write('DIR_BLOQUES = os.path.join("cdpedia", "bloques")\n')
    f.write('DIR_ASSETS = os.path.join("cdpedia", "assets")\n')
    f.write('DIR_INDICE = os.path.join("cdpedia", "indice")\n')
    f.write('IMAGES_PER_BLOCK = %d\n' % config.IMAGES_PER_BLOCK)
    f.write('ARTICLES_PER_BLOCK = %d\n' % config.ARTICLES_PER_BLOCK)
    f.close()

def preparaTemporal(procesar_articles):
    dtemp = config.DIR_TEMP
    if os.path.exists(dtemp):
        if not procesar_articles:
            # preparamos paths y vemos que todo esté ok
            src_indices = path.join(config.DIR_CDBASE, "cdpedia", "indice")
            src_bloques = config.DIR_BLOQUES
            if not os.path.exists(src_indices):
                print "ERROR: quiere evitar articulos pero no hay indices en", src_indices
                exit()
            if not os.path.exists(src_bloques):
                print "ERROR: quiere evitar articulos pero no hay bloques en", src_bloques
                exit()
            tmp_indices = path.join(dtemp, "indices_backup")
            tmp_bloques = path.join(dtemp, "bloques_backup")

            # movemos a backup, borramos todo, y restablecemos
            os.rename(src_indices, tmp_indices)
            os.rename(src_bloques, tmp_bloques)
            shutil.rmtree(path.join(dtemp,"cdroot"), ignore_errors=True)
            os.makedirs(path.join(config.DIR_CDBASE, "cdpedia"))
            os.rename(tmp_indices, src_indices)
            os.rename(tmp_bloques, src_bloques)

        else:
            shutil.rmtree(path.join(dtemp,"cdroot"), ignore_errors=True)
    else:
        os.makedirs(dtemp)


def build_tarball(tarball_name):
    """Build the tarball."""
    # the symlink must be something like 'cdroot' -> 'temp/nicename'
    base, cdroot = os.path.split(config.DIR_CDBASE)
    nice_name = os.path.join(base, tarball_name)
    os.symlink(cdroot, nice_name)

    # build the .tar positioned on the temp dir, and using the symlink for
    # all files to be under the nice name
    args = dict(base=base, tarname=tarball_name, cdroot=tarball_name)
    os.system("tar --dereference --xz --directory %(base)s --create "
              "-f %(tarname)s.tar.xz %(cdroot)s" % args)

    # remove the symlink
    os.remove(nice_name)


def update_mini(image_path):
    """ update cdpedia image using code + assets in current working copy"""
    # chequeo no estricto image_path apunta a una imagen de cdpedia
    deberia_estar = [image_path, 'cdpedia', 'bloques', '00000000.cdp']
    if not os.path.exists(os.path.join(*deberia_estar)):
        print 'Directorio no parece ser imagen de cdpedia'
        sys.exit(1)

    # adapt some config paths
    old_top_dir = config.DIR_CDBASE
    new_top_dir = image_path
    config.DIR_CDBASE = config.DIR_CDBASE.replace(old_top_dir, new_top_dir)
    config.DIR_ASSETS = config.DIR_ASSETS.replace(old_top_dir, new_top_dir)

    copiarSources()
    src_info = ''
    copiarAssets(src_info, os.path.join(new_top_dir, 'cdpedia', 'assets'))


def main(src_info, version, evitar_iso, verbose, desconectado,
         procesar_articles, include_windows, tarball):
    # don't affect the rest of the machine
    make_it_nicer()

    if procesar_articles:
        try:
            import SuffixTree
        except ImportError:
            print NO_ST_MSG

    articulos = path.join(src_info, "articles")

    mensaje("Comenzando!")
    preparaTemporal(procesar_articles)

    mensaje("Copiando los assets")
    copiarAssets(src_info, config.DIR_ASSETS)

    if procesar_articles:
        mensaje("Preprocesando")
        if not path.exists(articulos):
            print "\nERROR: No se encuentra el directorio %r" % articulos
            print "Este directorio es obligatorio para el procesamiento general"
            sys.exit()
        cantnew, cantold = preprocesar.run(articulos, verbose)
        print '  total %d páginas procesadas' % cantnew
        print '      y %d que ya estaban de antes' % cantold

        mensaje("Calculando los que quedan y los que no")
        preprocesar.calcula_top_htmls(version)

        mensaje("Generando el log de imágenes")
        taken, adesc = extraer.run(verbose)
        print '  total: %5d imágenes extraídas' % taken
        print '         %5d a descargar' % adesc
    else:
        mensaje("Evitamos procesar artículos y generar el log de imágenes")

    mensaje("Recalculando porcentajes de reducción")
    calcular.run(verbose, version)

    if not desconectado:
        mensaje("Descargando las imágenes de la red")
        download.traer(verbose)

    mensaje("Reduciendo las imágenes descargadas")
    reducir.run(verbose)

    mensaje("Emblocando las imágenes reducidas")
    # agrupamos las imagenes en bloques
    result = ImageManager.generar_bloques(verbose)
    print '  total: %d bloques con %d imags' % result

    if procesar_articles:
        mensaje("Generando el índice")
        result = cdpindex.generar_de_html(articulos, verbose)
        print '  total: %d archivos' % result

        mensaje("Generando los bloques de artículos")
        result = ArticleManager.generar_bloques(verbose)
        print '  total: %d bloques con %d archivos y %d redirects' % result
    else:
        mensaje("Evitamos generar el índice y los bloques")

    mensaje("Copiando las fuentes")
    copiarSources()

    mensaje("Copiando los indices")
    dest_src = path.join(config.DIR_CDBASE, "cdpedia", "indice")
    if os.path.exists(dest_src):
        shutil.rmtree(dest_src)
    shutil.copytree(config.DIR_INDICE, dest_src)

    if include_windows:
        mensaje("Copiando cosas para Windows")
        # generated by pyinstaller 2.0
        copy_dir("resources/autorun.win/cdroot", config.DIR_CDBASE)

    mensaje("Generamos la config para runtime")
    genera_run_config()

    if not evitar_iso:
        mensaje("Armamos el ISO")
        armarIso("cdpedia.iso")

    if tarball:
        mensaje("Armamos el tarball con %r" % (tarball,))
        build_tarball(tarball)

    mensaje("Todo terminado!")


if __name__ == "__main__":
    msg = u"""
Generar el iso o tarball de cdpedia
  generar.py [...options...] <version> <directorio>
    donde versión es qué vamos a generar (dev, cd, dvd5, etc)
    y directorio es el lugar donde está la info

Actualizar una imagen con los cambios de code + assets en esta working copy
  generar.py --update-mini <directorio>
    donde directorio es el lugar donde esta la imagen a actualizar.
    Las otras opciones son ignoradas en este caso.
"""

    parser = optparse.OptionParser()
    parser.set_usage(msg)
    parser.add_option("-n", "--no-iso", action="store_true",
                      dest="create_iso",
                      help="evita crear el ISO al final")
    parser.add_option("-w", "--no-windows", action="store_true",
                      dest="no_windows",
                      help="no incorpora todo lo extra para correr en Windows")
    parser.add_option("-t", "--tarball", metavar="NAME",
                      help="arma un tarball usando el nombre NAME")
    parser.add_option("-v", "--verbose", action="store_true",
                  dest="verbose", help="muestra info de lo que va haciendo")
    parser.add_option("-d", "--desconectado", action="store_true",
                  dest="desconectado", help="trabaja desconectado de la red")
    parser.add_option("-a", "--no-articles", action="store_true",
                  dest="noarticles",
                  help="no reprocesa todo lo relacionado con articulos")
    parser.add_option("-g", "--guppy", action="store_true",
                  dest="guppy", help="arranca con guppy/heapy prendido")

    parser.add_option("--update-mini", action="store_true",
                      dest="update_mini",
                      help="Actualiza una imagen con el code + assets de esta working copy.")


    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.print_help()
        exit()

    version = args[0]
    direct = args[1]
    if version not in config.VALID_VERSIONS:
        print "Not a valid version! try one of", config.VALID_VERSIONS
        exit()

    evitar_iso = bool(options.create_iso)
    include_windows = not bool(options.no_windows)
    verbose = bool(options.verbose)
    desconectado = bool(options.desconectado)
    procesar_articles = not bool(options.noarticles)

    if options.guppy:
        try:
            import guppy.heapy.RM
        except ImportError:
            print "ERROR: Tratamos de levantar heapy pero guppy no está instalado!"
            exit()
        guppy.heapy.RM.on()

    if options.update_mini:
        update_mini(direct)
    else:
        main(direct, version, evitar_iso, verbose, desconectado,
             procesar_articles, include_windows, options.tarball)
