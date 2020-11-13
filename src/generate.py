# Copyright 2008-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/

import datetime
import importlib
import logging
import optparse
import os
import shutil
import subprocess
import sys
import zipfile

from logging.handlers import RotatingFileHandler
from os import path

import yaml

import config
from src.preprocessing import preprocess
from src.armado.compresor import ArticleManager, ImageManager
from src.armado import cdpindex
from src.images import extract, download, scale, calculate, embed
from src.scraping import pydocs
from src.utiles import set_locale


# para poder hacer generar.py > log.txt
if sys.stdout.encoding is None:
    importlib.reload(sys)
    sys.setdefaultencoding('utf8')


# get a logger (may be already set up, or will set up in __main__)
logger = logging.getLogger('generar')


def link(src, dst):
    """Create a hard link, like os.link, only if needed."""
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    if not os.path.exists(dst):
        os.link(src, dst)


def make_it_nicer():
    """Make the process nicer at CPU and IO levels."""
    # cpu, simple
    if hasattr(os, 'nice'):
        os.nice(19)
    else:
        logger.warning("Platform without 'nice' support (running without optimizations)")

    # IO, much more complicated
    pid = os.getpid()
    try:
        subprocess.call(["ionice", "-c", "Idle", "-p", str(pid)])
    except OSError as e:
        logger.warning(
            "Platform without 'ionice' installed! (running without optimizations): %s", e)


def copy_dir(src_dir, dst_dir):
    """Copy a directory recursively.

    Will copy everything except compiled Python and hidden files
    """
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    for fname in os.listdir(src_dir):
        if fname.startswith("."):
            continue
        if fname.endswith('.pyc') or fname == "__pycache__":
            continue
        src_path = path.join(src_dir, fname)
        dst_path = path.join(dst_dir, fname)
        if path.isdir(src_path):
            copy_dir(src_path, dst_path)
        else:
            link(src_path, dst_path)


def copy_assets(src_info, dest):
    """Copy all the asset files."""
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

    # general info
    src_dir = "resources/general_info"
    copy_dir(src_dir, config.DIR_CDBASE)
    link('AUTHORS.txt', os.path.join(config.DIR_CDBASE, 'AUTORES.txt'))

    # institutional
    src_dir = "resources/institucional"
    dst_dir = path.join(dest, "institucional")
    copy_dir(src_dir, dst_dir)

    # dynamic stuff
    src_dir = path.join(src_info, "resources")
    dst_dir = path.join(dest, "dynamic")
    copy_dir(src_dir, dst_dir)


def copy_sources():
    """Copy the source code files."""
    # el src
    dest_src = path.join(config.DIR_CDBASE, "src")
    clean_dir(dest_src)
    link(path.join("src", "__init__.py"), dest_src)
    link(path.join("src", "utiles.py"), dest_src)
    copy_dir(path.join("src", "armado"), path.join(dest_src, "armado"))
    copy_dir(path.join("src", "web"), path.join(dest_src, "web"))

    # el main va al root
    link(path.join("src", "cdpedia.py"), config.DIR_CDBASE)

    if config.DESTACADOS:
        link(config.DESTACADOS, config.DIR_CDBASE)


def generate_libs():
    """Generate all needed libs."""
    dest_src = path.join(config.DIR_CDBASE, "extlib")
    cmd = [
        'pip', 'install',  # base command
        '--target={}'.format(dest_src),  # put all the resulting files in that specific dir
        '--requirement=requirements.txt',   # the running requirements
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    for line in proc.stdout:
        logger.debug(":: %s", line.rstrip())
    retcode = proc.wait()
    if retcode:
        raise RuntimeError("Pip failed")


def clean_dir(path):
    """Create a directory, and delete existing one if needed."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def build_iso(dest):
    """Build the final .iso."""
    dest = dest + ".iso"
    subprocess.call(["mkisofs", "-hide-rr-moved", "-quiet", "-f", "-V",
                     "CDPedia", "-volset", "CDPedia", "-o", dest, "-R",
                     "-J", config.DIR_CDBASE])


def gen_run_config(lang_config):
    """Generate the config file used on the final user computer."""
    f = open(path.join(config.DIR_CDBASE, "config.py"), "w")
    f.write('import os\n\n')
    f.write('VERSION = %s\n' % repr(config.VERSION))
    f.write('SERVER_MODE = %s\n' % config.SERVER_MODE)
    f.write('EDICION_ESPECIAL = %s\n' % repr(config.EDICION_ESPECIAL))
    f.write('HOSTNAME = "%s"\n' % config.HOSTNAME)
    f.write('PORT = %d\n' % config.PORT)
    f.write('PORTAL_PAGE = "%s"\n' % lang_config['portal_index'])
    f.write('ASSETS = %s\n' % config.ASSETS)
    f.write('ALL_ASSETS = %s\n' % config.ALL_ASSETS)
    f.write('DESTACADOS = {}\n'.format(config.DESTACADOS))
    f.write('BROWSER_WD_SECONDS = %d\n' % config.BROWSER_WD_SECONDS)
    f.write('SEARCH_RESULTS = %d\n' % config.SEARCH_RESULTS)
    f.write('LANGUAGE = "%s"\n' % config.LANGUAGE)
    f.write('URL_WIKIPEDIA = "%s"\n' % config.URL_WIKIPEDIA)
    f.write('PYTHON_DOCS_FILENAME = "%s"\n' % config.PYTHON_DOCS_FILENAME)
    f.write('LOCALE = "%s"\n' % os.environ['LANGUAGE'])
    f.write('DIR_BLOQUES = "bloques"\n')
    f.write('DIR_IMGBLOQUES = "images"\n')
    f.write('DIR_ASSETS = "assets"\n')
    f.write('DIR_INDICE = "indice"\n')
    f.write('IMAGES_PER_BLOCK = %d\n' % config.IMAGES_PER_BLOCK)
    f.write('ARTICLES_PER_BLOCK = %d\n' % config.ARTICLES_PER_BLOCK)
    f.write('NAMESPACES_PREFIXES_DIR = os.path.join("assets", "dynamic")\n')
    f.close()


def prepare_temporary_dirs(process_articles):
    """Create, clean or rerun using the previous state in logs."""
    dtemp = config.DIR_TEMP
    if os.path.exists(dtemp):
        if not process_articles:
            # preparamos paths y vemos que todo esté ok
            src_indices = path.join(config.DIR_CDBASE, "indice")
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
            shutil.rmtree(path.join(dtemp, "cdroot"), ignore_errors=True)
            os.rename(tmp_indices, src_indices)
            os.rename(tmp_bloques, src_bloques)

        else:
            shutil.rmtree(path.join(dtemp, "cdroot"), ignore_errors=True)
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


def main(lang, src_info, version, lang_config, gendate,
         verbose=False, desconectado=False, process_articles=True):
    """Generate the CDPedia tarball or iso."""
    # don't affect the rest of the machine
    make_it_nicer()

    # set language in config
    if config.LANGUAGE is None:
        config.LANGUAGE = lang
        config.URL_WIKIPEDIA = config.URL_WIKIPEDIA_TPL.format(lang=lang)

    # validate lang and versions, and fix config with selected data
    logger.info("Fixing config for lang=%r version=%r", lang, version)
    try:
        _lang_conf = config.imagtypes[lang]
    except KeyError:
        available_langs = list(config.imagtypes.keys())
        print("ERROR: %r is not a valid language! try one of %s" % (lang, available_langs))
        exit()
    try:
        config.imageconf = _lang_conf[version]
    except KeyError:
        available_versions = list(_lang_conf.keys())
        print("ERROR: %r is not a valid version! try one of %s" % (version, available_versions))
        exit()
    config.langconf = lang_config

    logger.info("Starting!")
    prepare_temporary_dirs(process_articles)

    logger.info("Copying the assets and locale files")
    copy_assets(src_info, os.path.join(config.DIR_CDBASE, 'assets'))
    link(os.path.join(src_info, 'portal_pages.txt'), config.DIR_TEMP)
    copy_dir('locale', path.join(config.DIR_CDBASE, "locale"))
    set_locale(lang_config.get('second_language'), record=True)

    articulos = path.join(src_info, "articles")
    if process_articles:
        logger.info("Preprocessing")
        if not path.exists(articulos):
            logger.error("Couldn't find articles dir: %r", articulos)
            raise EnvironmentError("Directory not found, can't continue")
            sys.exit()
        preprocess.run(articulos)

        logger.info("Calculating which stay and which don't")
        preprocess.pages_selector.calculate()

        logger.info("Generating the images log")
        taken, adesc = extract.run()
        logger.info("Extracted %d images, need to download %d", taken, adesc)
    else:
        logger.info("Avoid processing articles and generating images log")

    logger.info("Recalculating the reduction percentages.")
    calculate.run()

    if not desconectado:
        logger.info("Downloading the images from the internet")
        download.retrieve()

    logger.info("Reducing the downloaded images")
    scale.run(verbose)

    if config.EMBED_IMAGES:
        logger.info("Embedding selected images")
        embed.run()

    logger.info("Putting the reduced images into blocks")
    # agrupamos las imagenes en bloques
    q_blocks, q_images = ImageManager.generar_bloques(verbose)
    logger.info("Got %d blocks with %d images", q_blocks, q_images)

    if not process_articles:
        logger.info("Not generating index and blocks (by user request)")
    elif preprocess.pages_selector.same_info_through_runs:
        logger.info("Same articles than previous run "
                    "(not generating index and blocks)")
    else:
        logger.info("Generating the index")
        result = cdpindex.generate_from_html(articulos, verbose)
        logger.info("Got %d files", result)
        logger.info("Generating the articles blocks")
        q_blocks, q_files, q_redirs = ArticleManager.generar_bloques(lang,
                                                                     verbose)
        logger.info("Got %d blocks with %d files and %d redirects",
                    q_blocks, q_files, q_redirs)

    logger.info("Copying the sources and libs")
    copy_sources()
    generate_libs()

    # Copy python docs
    pydocs.clone(lang, lang_config, os.path.dirname(src_info))

    logger.info("Generating the links to blocks and indexes")
    # blocks
    dest = path.join(config.DIR_CDBASE, "bloques")
    if os.path.exists(dest):
        os.remove(dest)
    os.symlink(path.abspath(config.DIR_BLOQUES), dest)
    # images blocks
    dest = path.join(config.DIR_CDBASE, "images")
    if os.path.exists(dest):
        os.remove(dest)
    os.symlink(path.abspath(config.DIR_IMGBLOQUES), dest)
    # indexes
    dest = path.join(config.DIR_CDBASE, "indice")
    if os.path.exists(dest):
        os.remove(dest)
    os.symlink(path.abspath(config.DIR_INDICE), dest)

    if config.imageconf["windows"]:
        logger.info("Copying Windows stuff")
        copy_dir("resources/autorun.win/cdroot", config.DIR_CDBASE)
        # unpack embeddable python distribution for win32
        py_win_zip = "resources/autorun.win/python-win32.zip"
        py_win_dst = os.path.join(config.DIR_CDBASE, 'python')
        with zipfile.ZipFile(py_win_zip, 'r') as zh:
            zh.extractall(py_win_dst)

    logger.info("Generating runtime config")
    gen_run_config(lang_config)

    base_dest_name = "cdpedia-%s-%s-%s-%s" % (lang, config.VERSION, gendate, version)
    if config.imageconf["type"] == "iso":
        logger.info("Building the ISO: %r", base_dest_name)
        build_iso(base_dest_name)
    elif config.imageconf["type"] == "tarball":
        logger.info("Building the tarball: %r", base_dest_name)
        build_tarball(base_dest_name)
    else:
        raise ValueError("Unrecognized image type")

    logger.info("All done!")


class CustomRotatingFH(RotatingFileHandler):
    """Rotating handler that starts a new file for every run."""

    def __init__(self, *args, **kwargs):
        RotatingFileHandler.__init__(self, *args, **kwargs)
        self.doRollover()


if __name__ == "__main__":
    msg = """
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
                      dest="noarticles", help="no reprocesa todo lo relacionado con articulos")
    parser.add_option("-g", "--guppy", action="store_true",
                      dest="guppy", help="arranca con guppy/heapy prendido")

    (options, args) = parser.parse_args()

    if len(args) != 3:
        parser.print_help()
        exit()

    lang = args[0]
    version = args[1]
    direct = args[2]

    verbose = bool(options.verbose)
    desconectado = bool(options.desconectado)
    process_articles = not bool(options.noarticles)

    # setup logging
    _logger = logging.getLogger()
    handler = logging.StreamHandler()
    _logger.addHandler(handler)
    formatter = logging.Formatter(
        "%(asctime)s  %(name)-15s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    _logger.setLevel(logging.DEBUG)
    handler = CustomRotatingFH("generation.log")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)

    if options.guppy:
        try:
            import guppy.heapy.RM
        except ImportError:
            print("ERROR: Tried to start heapy but guppy is not installed!")
            exit()
        guppy.heapy.RM.on()

    with open('languages.yaml') as fh:
        _config = yaml.load(fh)
        try:
            lang_config = _config[lang]
        except KeyError:
            print("ERROR: there's no %r in 'languages.yaml'" % (lang,))
            exit()

    gendate = datetime.date.today().strftime("%Y%m%d")
    main(lang, direct, version, lang_config, gendate, verbose, desconectado, process_articles)
