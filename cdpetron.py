#!/usr/bin/env python

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

from __future__ import print_function

import StringIO
import argparse
import datetime
import gzip
import itertools
import logging
import os
import shutil
import sys
import urllib2
from logging.handlers import RotatingFileHandler

import yaml

# some constants to download the articles list we need to scrap
URL_LIST = (
    "http://dumps.wikimedia.org/%(language)swiki/latest/"
    "%(language)swiki-latest-all-titles-in-ns0.gz"
)
ART_ALL = "all_articles.txt"
DATE_FILENAME = "start_date.txt"
NAMESPACES = "namespace_prefixes.txt"

# base url
WIKI_BASE = 'http://%(language)s.wikipedia.org'

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


class Location(object):
    """Holder for the different working locations, presenting an enum-like interface.

    It also ensures that each dir is properly prefixed with selected language, and that it exists.
    """

    # the directory (inside the one specified by the user) that actually
    # holds the articles, images and resources
    ARTICLES = "articles"
    IMAGES = "images"
    RESOURCES = 'resources'

    def __init__(self, dumpdir, branchdir, language):
        self.dumpbase = os.path.abspath(dumpdir)
        self.branchdir = os.path.abspath(branchdir)

        self.langdir = os.path.join(self.dumpbase, language)
        self.articles = os.path.join(self.langdir, self.ARTICLES)
        self.resources = os.path.join(self.langdir, self.RESOURCES)
        self.images = os.path.join(self.dumpbase, self.IMAGES)  # language agnostic

        # (maybe) create all the above directories (except branchdir); note they are ordered!
        to_create = [
            self.dumpbase,
            self.langdir,
            self.articles,
            self.resources,
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
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter("%(asctime)s  %(name)-20s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
handler = CustomRotatingFH("cdpetron.log")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger = logging.getLogger("cdpetron")


def get_lists(language, lang_config, test):
    """Get the list of wikipedia articles."""
    # save the creation date everytime we start listing everything; this is the moment that
    # reflects better "when the wikipedia was created"
    gendate = save_creation_date()

    all_articles = os.path.join(location.langdir, ART_ALL)
    fh_artall = open(all_articles, "wb")

    url = URL_LIST % dict(language=language)
    logger.info("Getting list file: %r", url)
    u = urllib2.urlopen(url)
    logger.debug("Got headers: %s", u.headers.items())
    fh = StringIO.StringIO(u.read())
    gz = gzip.GzipFile(fileobj=fh)

    # walk through lines, easier to count and assure all lines are proper
    # saved into final file, mainly because of last line separator
    q = 0
    for line in gz:
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
        fh_artall.write(article.encode('utf8') + "\n")
        prefixes.add(article.split(":", 1)[0])
    tot += q
    logger.info("Got %d namespace articles", q)

    # save the namespace prefixes
    _path = os.path.join(location.resources, NAMESPACES)
    with open(_path, 'wb') as fh:
        for prefix in sorted(prefixes):
            fh.write(prefix.encode("utf8") + "\n")

    q = 0
    for page in lang_config['include']:
        q += 1
        fh_artall.write(page.encode('utf8') + "\n")
    tot += q
    logger.info("Have %d articles to mandatorily include", q)

    fh_artall.close()
    logger.info("Total of articles: %d", tot)

    return gendate


def save_creation_date():
    """Save the creation date of the CDPedia."""
    generation_date = datetime.date.today().strftime("%Y%m%d")
    _path = os.path.join(location.resources, DATE_FILENAME)
    with open(_path, 'wb') as f:
        f.write(generation_date + "\n")
    logger.info("Date of generation saved: %s", generation_date)
    return generation_date


def load_creation_date():
    """Load the creation date of the CDPedia.

    Having this in disk means that the lists were generated. Returns None if can't read it.
    """
    _path = os.path.join(location.resources, DATE_FILENAME)
    try:
        with open(_path, 'rb') as fh:
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
    #cmd = "python %s/utilities/scraper.py %s %s %s %s" % (
    #    location.branchdir, articles_file, language, location.articles, namespaces_path)
    #if test:
    #    cmd += " " + str(TEST_LIMIT_SCRAP)
    #res = os.system(cmd)
    #if res != 0:
    #    logger.error("Bad result code from scraping: %r", res)
    #    logger.error("Quitting, no point in continue")
    #    exit()


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


def scrap_extra_pages(language, extra_pages):
    """Scrap extra pages defined in a text file."""
    extra_pages_file = os.path.join(location.branchdir, extra_pages)
    _call_scraper(language, extra_pages_file)


def scrap_portals(language, lang_config):
    """Get the portal index and scrap it."""
    # get the portal url, get out if don't have it
    portal_index_url = lang_config.get('portal_index')
    if portal_index_url is None:
        logger.info("Not scraping portals, url not configured.")
        return

    logger.info("Downloading portal index from %r", portal_index_url)
    u = urllib2.urlopen(portal_index_url)
    html = u.read()
    logger.info("Scrapping portals page of lenght %d", len(html))
    items = portals.parse(language, html)
    logger.info("Generating portals html with %d items", len(items))
    new_html = portals.generate(items)

    # save it
    with open(os.path.join(location.resources, "portals.html"), 'wb') as fh:
        fh.write(new_html)
    logger.info("Portal scraping done")


def clean(keep_processed):
    """Clean and setup the temp directory."""
    # let's create a temp directory for the generation with a symlink to
    # images (clean it first if already there). Note that 'temp' and
    # 'images' are hardcoded here, as this is what expects
    # the generation part)
    temp_dir = os.path.join(location.branchdir, "temp")
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
    logger.info("Branch directory: %r", location.branchdir)
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

    if not noscrap:
        scrap_portals(language, lang_config)
        scrap_pages(language, test)

    if extra_pages:
        scrap_extra_pages(language, extra_pages)

    if test:
        image_type = 'beta'
    if image_type is None:
        if not noscrap:
            # new articles! do a full clean before, including the "processed" files
            clean(keep_processed=False)
        for image_type in imag_config:
            logger.info("Generating image for type: %r", image_type)
            clean(keep_processed=True)
            generate.main(
                language, location.langdir, location.branchdir, image_type,
                lang_config, gendate, verbose=test)
    else:
        logger.info("Generating image for type %r only", image_type)
        if not noclean:
            # keep previous processed if not new scraped articles and not testing
            keep_processed = noscrap and not test
            clean(keep_processed=keep_processed)
        generate.main(
            language, location.langdir, location.branchdir, image_type,
            lang_config, gendate, verbose=test)


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
                        help="Work on a few pages only")
    parser.add_argument("--image-type",
                        help="Don't clean the temp dir, useful to resume the "
                             "generation of an image; need to be paired with "
                             "'--image-type' option")
    parser.add_argument("branch_dir",
                        help="The project branch to use.")
    parser.add_argument("dump_dir",
                        help="A directory to store all articles and images.")
    parser.add_argument("language",
                        help="The two-letters language name.")
    parser.add_argument("--extra-pages",
                        help="file with extra pages to be included in the image.")
    args = parser.parse_args()

    if args.no_clean and not args.image_type:
        logger.error("--no-clean option is only usable when --image-type was indicated")
        exit()

    location = Location(args.dump_dir, args.branch_dir, args.language)

    # get the language config
    _config_fname = os.path.join(location.branchdir, 'languages.yaml')
    with open(_config_fname) as fh:
        _config = yaml.safe_load(fh)
        try:
            lang_config = _config[args.language]
        except KeyError:
            logger.error("there's no %r in language config file %r", args.language, _config_fname)
            exit()
    logger.info("Opened succesfully language config file %r", _config_fname)

    # get the image type config
    _config_fname = os.path.join(location.branchdir, 'imagtypes.yaml')
    with open(_config_fname) as fh:
        _config = yaml.safe_load(fh)
        try:
            imag_config = _config[args.language]
        except KeyError:
            logger.error("there's no %r in image type config file %r",
                         args.language, _config_fname)
            exit()
    logger.info("Opened succesfully image type config file %r", _config_fname)
    if args.image_type:
        if args.image_type not in imag_config:
            logger.error("there's no %r image in the image type config",
                         args.image_type)
            exit()

    # branch dir must exist
    if not os.path.exists(location.branchdir):
        logger.error("The branch dir doesn't exist!")
        exit()

    # fix sys path to branch dir and import the rest of stuff from there
    sys.path.insert(1, location.branchdir)
    sys.path.insert(1, os.path.join(location.branchdir, "utilities"))
    from src import list_articles_by_namespaces, generate
    from src.scraping import portals, scraper

    main(
        args.language, lang_config, imag_config, nolists=args.no_lists, noscrap=args.no_scrap,
        noclean=args.no_clean, image_type=args.image_type, test=args.test_mode,
        extra_pages=args.extra_pages)
