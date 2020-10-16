#!/usr/bin/env python3

# Copyright 2014-2020 CDPedistas (see AUTHORS.txt)
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

import argparse
import codecs
import datetime
import gzip
import io
import itertools
import logging
import os
import shutil
import sys
import urllib.parse
import urllib.request
from logging.handlers import RotatingFileHandler
from tempfile import NamedTemporaryFile

import bs4
import yaml

import config
from utilities import localize
from src import list_articles_by_namespaces, generate
from src.armado import to3dirs
from src.preprocessing import preprocessors
from src.scraping import scraper, pydocs, css


# some constants to download the articles list we need to scrap
URL_LIST = (
    "http://dumps.wikimedia.org/%(language)swiki/latest/"
    "%(language)swiki-latest-all-titles-in-ns0.gz"
)
ART_ALL = "all_articles.txt"
DATE_FILENAME = "start_date.txt"
NAMESPACES = "namespace_prefixes.txt"
PORTAL_PAGES = 'portal_pages.txt'

# some limits when running in test mode
TEST_LIMIT_NAMESPACE = 50
TEST_LIMIT_SCRAP = 1000

# files/dirs to not remove if we want to keep the processed info during cleaning
KEEP_PROCESSED = [
    'preprocesado.txt',
    'preprocesado',
    'titles.txt',
    'page_scores_accum.txt',
    'page_scores_final.txt',
    'redirects.txt',
]


class Location:
    """Holder for the different working locations, presenting an enum-like interface.

    It also ensures that each dir is properly prefixed with selected language, and that it exists.
    """

    # the directory (inside the one specified by the user) that actually
    # holds the articles, images and resources
    ARTICLES = "articles"
    IMAGES = "images"
    RESOURCES = 'resources'

    def __init__(self, dumpdir, language):
        self.dumpbase = os.path.abspath(dumpdir)

        self.langdir = os.path.join(self.dumpbase, language)
        self.articles = os.path.join(self.langdir, self.ARTICLES)
        self.resources = os.path.join(self.langdir, self.RESOURCES)
        self.cssdir = os.path.join(self.resources, config.CSS_DIRNAME)
        self.images = os.path.join(self.dumpbase, self.IMAGES)  # language agnostic

        # (maybe) create all the above directories; note they are ordered!
        to_create = [
            self.dumpbase,
            self.langdir,
            self.articles,
            self.resources,
            self.cssdir,
            self.images,
        ]
        for item in to_create:
            if not os.path.exists(item):
                os.mkdir(item)


class CustomRotatingFH(RotatingFileHandler):
    """Rotating handler that starts a new file for every run."""

    def __init__(self, *args, **kwargs):
        RotatingFileHandler.__init__(self, *args, **kwargs)
        self.doRollover()


# set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s  %(name)-20s %(levelname)-8s %(message)s")

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

handler = CustomRotatingFH("cdpetron.log")
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)

logger = logging.getLogger("cdpetron")


def get_lists(language, lang_config, test):
    """Get the list of wikipedia articles."""
    # save the creation date everytime we start listing everything; this is the moment that
    # reflects better "when the wikipedia was created"
    gendate = save_creation_date()

    all_articles = os.path.join(location.langdir, ART_ALL)
    fh_artall = open(all_articles, "wt", encoding="utf-8")

    url = URL_LIST % dict(language=language)
    logger.info("Getting list file: %r", url)
    u = urllib.request.urlopen(url)
    logger.debug("Got headers: %s", list(u.headers.items()))
    fh = io.BytesIO(u.read())
    gz = gzip.GzipFile(fileobj=fh)

    # walk through lines, easier to count and assure all lines are proper
    # saved into final file, mainly because of last line separator
    q = 0
    for line in codecs.getreader("utf-8")(gz):
        fh_artall.write(line.strip() + "\n")
        q += 1
    tot = q
    gz.close()
    logger.info("Downloaded %d general articles", q)

    if test:
        test = TEST_LIMIT_NAMESPACE
    logger.info("Getting the articles from namespaces (with limit=%s)", test)
    q = 0
    prefixes = set()
    for article in list_articles_by_namespaces.get_articles(language, test):
        q += 1
        fh_artall.write(article + "\n")
        prefixes.add(article.split(":", 1)[0])
    tot += q
    logger.info("Got %d namespace articles", q)

    # save the namespace prefixes
    _path = os.path.join(location.resources, NAMESPACES)
    with open(_path, 'wt', encoding="utf-8") as fh:
        for prefix in sorted(prefixes):
            fh.write(prefix + "\n")

    q = 0
    for page in lang_config['include']:
        q += 1
        fh_artall.write(page + "\n")
    tot += q
    logger.info("Have %d articles to mandatorily include", q)

    fh_artall.close()
    logger.info("Total of articles: %d", tot)

    return gendate


def save_creation_date():
    """Save the creation date of the CDPedia."""
    generation_date = datetime.date.today().strftime("%Y%m%d")
    _path = os.path.join(location.resources, DATE_FILENAME)
    with open(_path, 'w', encoding="utf-8") as f:
        f.write(generation_date + "\n")
    logger.info("Date of generation saved: %s", generation_date)
    return generation_date


def load_creation_date():
    """Load the creation date of the CDPedia.

    Having this in disk means that the lists were generated. Returns None if can't read it.
    """
    _path = os.path.join(location.resources, DATE_FILENAME)
    try:
        with open(_path, 'r', encoding="utf-8") as fh:
            generation_date = fh.read().strip()
    except IOError:
        return
    logger.info("Date of generation loaded: %s", generation_date)
    return generation_date


def _call_scraper(language, articles_file, test=False):
    """Prepare the command and run scraper.py."""
    logger.info("Let's scrap (with limit=%s)", test)
    namespaces_path = os.path.join(location.resources, NAMESPACES)
    limit = TEST_LIMIT_SCRAP if test else None
    scraper.main(articles_file, language, location.articles, namespaces_path, test_limit=limit)


def scrap_pages(language, test):
    """Get the pages from wikipedia."""
    all_articles = os.path.join(location.langdir, ART_ALL)
    _call_scraper(language, all_articles, test)

    logger.info("Checking scraped size")
    total = os.stat(location.articles).st_size
    for dirpath, dirnames, filenames in os.walk(location.articles):
        for name in itertools.chain(dirnames, filenames):
            size = os.stat(os.path.join(dirpath, name)).st_size

            # consider that the file occupies whole 512 blocks
            blocks, tail = divmod(size, 512)
            if tail:
                blocks += 1
            total += blocks * 512
    logger.info("Total size of scraped articles: %d MB", total // 1024 ** 2)


def scrap_portal(language, lang_config):
    """Get the portal index and scrap it."""
    # get the portal url, get out if don't have it
    portal_index_title = lang_config.get('portal_index')
    if portal_index_title is None:
        logger.info("Not scraping portals, url not configured.")
        return

    logger.info("Scraping portal main page %s", portal_index_title)
    with NamedTemporaryFile('wt', encoding='utf8', dir='/tmp/', prefix='cdpedia-') as tf:
        tf.write(portal_index_title + '\n')
        tf.flush()
        _call_scraper(language, tf.name)

    dir3, quoted_page = to3dirs.get_path_file(portal_index_title)
    portal_filepath = os.path.join(location.articles, dir3, quoted_page)

    logger.info("Parsing portal page")
    with open(portal_filepath, 'rt', encoding='utf8') as fh:
        soup = bs4.BeautifulSoup(fh, features="html.parser")

    cnt = 0
    _path = os.path.join(location.langdir, PORTAL_PAGES)
    with open(_path, 'wt', encoding='utf8') as fh:
        for page in preprocessors.extract_pages(soup):
            cnt += 1
            fh.write(page + '\n')

    logger.info("Scraping portal sub pages (total=%d)", cnt)
    _call_scraper(language, _path)

    logger.info("Portal scraping done")


def clean(keep_processed):
    """Clean and setup the temp directory."""
    # let's create a temp directory for the generation with a symlink to
    # images (clean it first if already there). Note that 'temp' and
    # 'images' are hardcoded here, as this is what expects
    # the generation part)
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        # start it fresh
        logger.info("Temp dir setup fresh: %r", temp_dir)
        os.mkdir(temp_dir)
        os.symlink(location.images, os.path.join(temp_dir, "images"))
        return

    # remove (maybe) all stuff inside
    logger.info("Recursive deletion of old temp dir: %r (keep_processed=%s)",
                temp_dir, keep_processed)
    for item in os.listdir(temp_dir):
        if keep_processed and item in KEEP_PROCESSED:
            continue
        if item == 'images':
            continue
        path = os.path.join(temp_dir, item)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def main(language, lang_config, imag_config,
         nolists, noscrap, noclean, image_type, test, extra_pages):
    """Main entry point."""
    logger.info("Dump directory: %r", location.dumpbase)
    logger.info("Generating for language: %r", language)
    logger.info("Language config: %r", lang_config)
    logger.info("Options: nolists=%s noscrap=%s noclean=%s test=%s",
                nolists, noscrap, noclean, test)

    if nolists:
        gendate = load_creation_date()
        if gendate is None:
            logger.error("No article list available. Run at least once without --no-lists")
            return
    else:
        gendate = get_lists(language, lang_config, test)

    # setup css output before any scraping
    css.link_extractor.setup(location.cssdir)

    if not noscrap:
        scrap_portal(language, lang_config)
        scrap_pages(language, test)
        pydocs.download(language, lang_config, location.dumpbase)
        css.scrap_css()

    if extra_pages:
        _call_scraper(language, extra_pages)
        css.scrap_css()

    if config.VALIDATE_TRANSLATION:
        tr_updated, tr_complete, tr_compiled = localize.translation_status(language)
        if not tr_compiled:
            logger.error("No .mo file for chosen language, generation interrupted")
            return
        if tr_complete and tr_updated:
            logger.info("Translation to '%s' complete and up to date", language)
        else:
            logger.warning('Bad translation: complete=%s updated=%s', tr_complete, tr_updated)
            if not test and not tr_updated:
                # outdated translation may cause cdpedia run time errors
                logger.error('Language validation failed, generation interrupted')
                return

    if test and not image_type:
        image_type = ['beta']
    if image_type is None:
        image_type = ['tarbig']
    for image in image_type:
        logger.info("Generating image for type %r only", image)
        if not noclean:
            # keep previous processed if not new scraped articles and not testing
            keep_processed = noscrap and not test
            clean(keep_processed=keep_processed)
        generate.main(language, location.langdir, image, lang_config, gendate, verbose=test)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDPedia images")
    parser.add_argument("--no-lists", action='store_true',
                        help="Don't list all the articles from server")
    parser.add_argument("--no-scrap", action='store_true',
                        help="Don't scrap all the articles from server")
    parser.add_argument("--no-clean", action='store_true',
                        help="Don't clean the temp dir, useful to resume the "
                             "generation of an image; need to be paired with "
                             "'--image-type' option")
    parser.add_argument("--test-mode", action='store_true',
                        help="Work on a few pages only "
                        "(1000 default pages)")
    parser.add_argument("-p", "--page-limit", type=int,
                        help="Change default limit pages in test mode")
    parser.add_argument("--image-type",
                        help="'--image-type <option(s)>' select the standar options "
                             "to build CDPedia, "
                             "e.g. '--image-type cd,dvd9...'without spaces between image names"
                             "or just an image. "
                             "'tarbig' default if not set '--image-type'")
    parser.add_argument("-l", "--image-list", action="store_true",
                        help="Show images available in the selected language")
    parser.add_argument("dump_dir",
                        help="A directory to store all articles and images.")
    parser.add_argument("language",
                        help="The two-letters language name.")
    parser.add_argument("--extra-pages",
                        help="file with extra pages to be included in the image.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Show more progress information.")
    args = parser.parse_args()

    if args.no_clean and not args.image_type:
        logger.error("--no-clean option is only usable when --image-type was indicated")
        exit()

    location = Location(args.dump_dir, args.language)

    if args.verbose:
        stdout_handler.setLevel(logging.DEBUG)

    # set language config
    config.LANGUAGE = args.language
    config.URL_WIKIPEDIA = config.URL_WIKIPEDIA_TPL.format(lang=args.language)

    # get the image type config
    _config_fname = 'imagtypes.yaml'
    with open(_config_fname, 'rt', encoding="utf-8") as fh:
        _config = yaml.safe_load(fh)
        try:
            imag_config = _config[args.language]
        except KeyError:
            logger.error("there's no %r in image type config file %r",
                         args.language, _config_fname)
            exit()
    if args.image_list:
        print('{:10}{:10}{:10}'.format('Image', 'Format', 'Max. pages'))
        print('=' * 30)
        for data in sorted(imag_config):
            print('{:10}{:10}{:10}'.format(data, imag_config[data]['type'],
                  imag_config[data]['page_limit']))
        exit()
    logger.info("Opened succesfully image type config file %r", _config_fname)
    if args.image_type:
        args.image_type = args.image_type.split(',')
        for image in args.image_type:
            if image not in imag_config:
                logger.error("there's no %r image in the image type config", image)
                exit()

    # get the language config
    _config_fname = 'languages.yaml'
    with open(_config_fname) as fh:
        _config = yaml.safe_load(fh)
        try:
            lang_config = _config[args.language]
        except KeyError:
            logger.error("there's no %r in language config file %r", args.language, _config_fname)
            exit()
    logger.info("Opened succesfully language config file %r", _config_fname)

    # change page limit in test mode
    if args.page_limit:
        TEST_LIMIT_SCRAP = args.page_limit

    main(
        args.language, lang_config, imag_config, nolists=args.no_lists, noscrap=args.no_scrap,
        noclean=args.no_clean, image_type=args.image_type, test=args.test_mode,
        extra_pages=args.extra_pages)
