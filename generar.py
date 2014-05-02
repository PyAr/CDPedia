# -- encoding: utf-8 --

from __future__ import with_statement

import logging
import optparse
import os
import shutil
import subprocess
import sys

from os import path

#Para poder hacer generar.py > log.txt
if sys.stdout.encoding is None:
    reload(sys)
    sys.setdefaultencoding('utf8')

import config
from src.preproceso import preprocesar
from src.armado.compresor import ArticleManager, ImageManager
from src.armado import cdpindex
from src.armado.compressed_index import NO_ST_MSG
from src.imagenes import extract, download, reducir, calcular

# get a logger (may be already set up, or will set up in __main__)
logger = logging.getLogger('generar')

def make_it_nicer():
    """Make the process nicer at CPU and IO levels."""
    # cpu, simple
    os.nice(19)

    # IO, much more complicated
    pid = os.getpid()
    subprocess.call(["ionice", "-c", "Idle", "-p", str(pid)])


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
            logger.error("Mandatory directory not found: %r", src_dir)
            raise EnvironmentError("Directory not found, can't continue")
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


def build_iso(dest):
    """Build the final .iso."""
    dest = dest + ".iso"
    os.system("mkisofs -hide-rr-moved -quiet -f -V CDPedia -volset "
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
                logger.error("Want to avoid article processing but didn't "
                             "find indexes in %r", src_indices)
                raise EnvironmentError("Indexes not found, can't continue")
            if not os.path.exists(src_bloques):
                logger.error("Want to avoid article processing but didn't "
                             "find blocks in %r", src_bloques)
                raise EnvironmentError("Blocks not found, can't continue")
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
    """Update cdpedia image using code + assets in current working copy."""
    # chequeo no estricto image_path apunta a una imagen de cdpedia
    deberia_estar = [image_path, 'cdpedia', 'bloques', '00000000.cdp']
    if not os.path.exists(os.path.join(*deberia_estar)):
        logger.error("The directory doesn't look like a CDPedia image.")
        raise EnvironmentError("CDPedia image not found, can't continue")

    # adapt some config paths
    old_top_dir = config.DIR_CDBASE
    new_top_dir = image_path
    config.DIR_CDBASE = config.DIR_CDBASE.replace(old_top_dir, new_top_dir)
    config.DIR_ASSETS = config.DIR_ASSETS.replace(old_top_dir, new_top_dir)

    copiarSources()
    src_info = ''
    copiarAssets(src_info, os.path.join(new_top_dir, 'cdpedia', 'assets'))


def main(lang, src_info, version,
         verbose=False, desconectado=False, procesar_articles=True):
    # don't affect the rest of the machine
    make_it_nicer()

    if procesar_articles:
        try:
            import SuffixTree
        except ImportError:
            logger.warning(NO_ST_MSG)

    # validate lang and versions, and fix config with selected data
    logger.info("Fixing config for lang=%r version=%r", lang, version)
    try:
        _lang_conf = config.imagtypes[lang]
    except KeyError:
        print "Not a valid language! try one of", config.imagtypes.keys()
        exit()
    try:
        config.imageconf = _lang_conf[version]
    except KeyError:
        print "Not a valid version! try one of", _lang_conf.keys()
        exit()

    logger.info("Starting!")
    preparaTemporal(procesar_articles)

    logger.info("Copying the assets")
    copiarAssets(src_info, config.DIR_ASSETS)

    articulos = path.join(src_info, "articles")
    if procesar_articles:
        logger.info("Preprocessing")
        if not path.exists(articulos):
            logger.error("Couldn't find articles dir: %r", articulos)
            raise EnvironmentError("Directory not found, can't continue")
            sys.exit()
        cantnew, cantold = preprocesar.run(articulos, verbose)
        logger.info("Processed pages: %d new, %d from before",
                    cantnew, cantold)

        logger.info("Calculating which stay and which don't")
        preprocesar.pages_selector.calculate()

        logger.info("Generating the images log")
        taken, adesc = extract.run()
        logger.info("Extracted %d images, need to download %d", taken, adesc)
    else:
        logger.info("Avoid processing articles and generating images log")

    logger.info("Recalculating the reduction percentages.")
    calcular.run(verbose)

    if not desconectado:
        logger.info("Downloading the images from the internet")
        download.traer(verbose)

    logger.info("Reducing the downloaded images")
    reducir.run(verbose)

    logger.info("Putting the reduced images into blocks")
    # agrupamos las imagenes en bloques
    q_blocks, q_images = ImageManager.generar_bloques(verbose)
    logger.info("Got %d blocks with %d images", q_blocks, q_images)

    if not procesar_articles:
        logger.info("Not generating index and blocks (by user request)")
    elif preprocesar.pages_selector.same_info_through_runs:
        logger.info("Same articles than previous run "
                     "(not generating index and blocks)")
    else:
        logger.info("Generating the index")
        result = cdpindex.generar_de_html(articulos, verbose)
        logger.info("Got %d files", result)
        logger.info("Generating the articles blocks")
        q_blocks, q_files, q_redirs = ArticleManager.generar_bloques(verbose)
        logger.info("Got %d blocks with %d files and %d redirects",
                    q_blocks, q_files, q_redirs)

    logger.info("Copying the sources")
    copiarSources()

    logger.info("Generating the links to blocks and indexes")
    # blocks
    dest = path.join(config.DIR_CDBASE, "cdpedia", "bloques")
    if os.path.exists(dest):
        os.remove(dest)
    os.symlink(path.abspath(config.DIR_BLOQUES), dest)
    # indexes
    dest = path.join(config.DIR_CDBASE, "cdpedia", "indice")
    if os.path.exists(dest):
        os.remove(dest)
    os.symlink(path.abspath(config.DIR_INDICE), dest)

    if config.imageconf["windows"]:
        logger.info("Copying Windows stuff")
        # generated by pyinstaller 2.0
        copy_dir("resources/autorun.win/cdroot", config.DIR_CDBASE)

    logger.info("Generating runtime config")
    genera_run_config()

    if config.imageconf["type"] == "iso":
        dest_name = "cdpedia-%s-%s" % (config.VERSION, version)
        logger.info("Building the ISO: %r", dest_name)
        build_iso(dest_name)
    elif config.imageconf["type"] == "tarball":
        dest_name = "cdpedia-%s-%s" % (config.VERSION, version)
        logger.info("Building the tarball: %r", dest_name)
        build_tarball(dest_name)
    else:
        raise ValueError("Unrecognized image type")

    logger.info("All done!")


if __name__ == "__main__":
    msg = u"""
Generate the CDPedia tarball or iso.

  generar.py [...options...] <lang> <version> <directory>
    - lang: the CDPedia language (es, pt, etc)
    - version: the version to generate (dev, cd, dvd5, etc)
    - directory: where is all the source data

To update an image with the code and assets changes  in this working copy:
  generar.py --update-mini <directory>
    - directory is where the image to update is
    (all other options are ignored in this case)
"""

    parser = optparse.OptionParser()
    parser.set_usage(msg)
    parser.add_option("-v", "--verbose", action="store_true",
                  dest="verbose", help="muestra info de lo que va haciendo")
    parser.add_option("-d", "--desconectado", action="store_true",
                  dest="desconectado", help="trabaja desconectado de la red")
    parser.add_option("-a", "--no-articles", action="store_true",
                  dest="noarticles",
                  help="no reprocesa todo lo relacionado con articulos")
    parser.add_option("-g", "--guppy", action="store_true",
                  dest="guppy", help="arranca con guppy/heapy prendido")

    parser.add_option("--update-mini", action="store_true", dest="update_mini",
                      help="Actualiza una imagen con el code + assets de "
                           "esta working copy.")

    (options, args) = parser.parse_args()

    if len(args) != 3:
        parser.print_help()
        exit()

    lang = args[0]
    version = args[1]
    direct = args[2]

    verbose = bool(options.verbose)
    desconectado = bool(options.desconectado)
    procesar_articles = not bool(options.noarticles)

    # setup logging
    _logger = logging.getLogger()
    handler = logging.StreamHandler()
    _logger.addHandler(handler)
    formatter = logging.Formatter(
        "%(asctime)s  %(name)-15s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    _logger.setLevel(logging.DEBUG)

    if options.guppy:
        try:
            import guppy.heapy.RM
        except ImportError:
            print "ERROR: Tried to start heapy but guppy is not installed!"
            exit()
        guppy.heapy.RM.on()

    if options.update_mini:
        update_mini(direct)
    else:
        main(lang, direct, version, verbose, desconectado, procesar_articles)
