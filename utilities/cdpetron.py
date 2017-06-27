#!//usr/bin/env python

# Copyright 2014-2017 CDPedistas (see AUTHORS.txt)
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
# For further info, check  https://launchpad.net/cdpedia/

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

import yaml

# some constants to download the articles list we need to scrap
URL_LIST = (
    "http://dumps.wikimedia.org/%(language)swiki/latest/"
    "%(language)swiki-latest-all-titles-in-ns0.gz"
)
ART_ALL = "all_articles.txt"
DATE_FILENAME = "start_date.txt"
NAMESPACES = "namespace_prefixes.txt"

# the directory (inside the one specified by the user) that actually
# holds the articles, images and resources
DUMP_ARTICLES = "articles"
DUMP_IMAGES = "images"
DUMP_RESOURCES = 'resources'

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

# set up logging
logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s  %(name)-20s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger = logging.getLogger("cdpetron")


def get_lists(branch_dir, language, config, test):
    """Get the list of wikipedia articles."""
    gendate = datetime.date.today().strftime("%Y%m%d")
    with open(DATE_FILENAME, 'wb') as fh:
        fh.write(gendate + "\n")

    fh_artall = open(ART_ALL, "wb")

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
    direct = os.path.join(dump_dir, language, DUMP_RESOURCES)
    if not os.path.exists(direct):
        os.mkdir(direct)
    _path = os.path.join(direct, NAMESPACES)
    with open(_path, 'wb') as fh:
        for prefix in sorted(prefixes):
            fh.write(prefix.encode("utf8") + "\n")

    q = 0
    for page in config['include']:
        q += 1
        fh_artall.write(page.encode('utf8') + "\n")
    tot += q
    logger.info("Have %d articles to mandatorily include", q)

    fh_artall.close()
    logger.info("Total of articles: %d", tot)
    return gendate


def scrap_pages(branch_dir, language, dump_lang_dir, test):
    """Get the pages from wikipedia."""
    articles_dir = os.path.join(dump_lang_dir, DUMP_ARTICLES)
    logger.info("Assure articles dir is empty: %r", articles_dir)
    if os.path.exists(articles_dir):
        shutil.rmtree(articles_dir)
    os.mkdir(articles_dir)

    logger.info("Let's scrap (with limit=%s)", test)
    assert os.getcwd() == dump_lang_dir
    namespaces_path = os.path.join(dump_lang_dir, DUMP_RESOURCES, NAMESPACES)
    cmd = "python %s/utilities/scraper.py %s %s %s %s" % (
        branch_dir, ART_ALL, language, DUMP_ARTICLES, namespaces_path)
    if test:
        cmd += " " + str(TEST_LIMIT_SCRAP)
    res = os.system(cmd)
    if res != 0:
        logger.error("Bad result code from scrapping: %r", res)
        logger.error("Quitting, no point in continue")
        exit()

    logger.info("Checking scraped size")
    total = os.stat(articles_dir).st_size
    for dirpath, dirnames, filenames in os.walk(articles_dir):
        for name in itertools.chain(dirnames, filenames):
            size = os.stat(os.path.join(dirpath, name)).st_size

            # consider that the file occupies whole 512 blocks
            blocks, tail = divmod(size, 512)
            if tail:
                blocks += 1
            total += blocks * 512
    logger.info("Total size of scraped articles: %d MB", total // 1024 ** 2)


def scrap_portals(dump_lang_dir, language, lang_config):
    """Get the portal index and scrap it."""
    # always create the resources directory
    direct = os.path.join(dump_lang_dir, DUMP_RESOURCES)
    if not os.path.exists(direct):
        os.mkdir(direct)

    # get the portal url, get out if don't have it
    portal_index_url = lang_config.get('portal_index')
    if portal_index_url is None:
        logger.info("Not scrapping portals, url not configured.")
        return

    logger.info("Downloading portal index from %r", portal_index_url)
    u = urllib2.urlopen(portal_index_url)
    html = u.read()
    logger.info("Scrapping portals page of lenght %d", len(html))
    items = portals.parse(language, html)
    logger.info("Generating portals html with %d items", len(items))
    new_html = portals.generate(items)

    # save it
    with open(os.path.join(direct, "portals.html"), 'wb') as fh:
        fh.write(new_html)
    logger.info("Portal scrapping done")


def clean(branch_dir, dump_dir, keep_processed):
    """Clean and setup the temp directory."""
    # we need a directory for the images in the dump dir (but keep it
    # if already there, we want to cache images!)
    image_dump_dir = os.path.join(dump_dir, DUMP_IMAGES)
    logger.info("Assure directory for images is there: %r", image_dump_dir)
    if not os.path.exists(image_dump_dir):
        os.mkdir(image_dump_dir)

    # let's create a temp directory for the generation with a symlink to
    # images (clean it first if already there). Note thtat 'temp' and
    # 'images' are hardcoded here, as this is what expects
    # the generation part)
    temp_dir = os.path.join(branch_dir, "temp")
    if not os.path.exists(temp_dir):
        # start it fresh
        logger.info("Temp dir setup fresh: %r", temp_dir)
        os.mkdir(temp_dir)
        os.symlink(image_dump_dir, os.path.join(temp_dir, "images"))
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


def main(branch_dir, dump_dir, language, lang_config, imag_config,
         nolists, noscrap, noclean, image_type, test):
    """Main entry point."""
    logger.info("Branch directory: %r", branch_dir)
    logger.info("Dump directory: %r", dump_dir)
    logger.info("Generating for language: %r", language)
    logger.info("Language config: %r", lang_config)
    logger.info("Options: nolists=%s noscrap=%s noclean=%s test=%s",
                nolists, noscrap, noclean, test)

    # images are common, but articles are separated by lang
    dump_imags_dir = dump_dir
    dump_lang_dir = os.path.join(dump_dir, language)

    logger.info("Assure directory for articles is there: %r", dump_lang_dir)
    if not os.path.exists(dump_lang_dir):
        os.mkdir(dump_lang_dir)
    os.chdir(dump_lang_dir)

    if not nolists:
        gendate = get_lists(branch_dir, language, lang_config, test)
    else:
        with open(DATE_FILENAME, 'rt') as fh:
            gendate = fh.read().strip()
    logger.info("Date of generation: %s", gendate)

    if not noscrap:
        scrap_portals(dump_lang_dir, language, lang_config)
        scrap_pages(branch_dir, language, dump_lang_dir, test)

    os.chdir(branch_dir)

    if test:
        image_type = 'beta'
    if image_type is None:
        if not noscrap:
            # new articles! do a full clean before, including the "processed" files
            clean(branch_dir, dump_imags_dir, keep_processed=False)
        for image_type in imag_config:
            logger.info("Generating image for type: %r", image_type)
            clean(branch_dir, dump_imags_dir, keep_processed=True)
            generar.main(language, dump_lang_dir, image_type, lang_config, gendate, verbose=test)
    else:
        logger.info("Generating image for type %r only", image_type)
        if not noclean:
            # keep previous processed if not new scrapped articles and not testing
            keep_processed = noscrap and not test
            clean(branch_dir, dump_imags_dir, keep_processed=keep_processed)
        generar.main(language, dump_lang_dir, image_type, lang_config, gendate, verbose=test)


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
    args = parser.parse_args()

    if args.no_clean and not args.image_type:
        print("ERROR: --no-clean option is only usable when --image-type was indicated")
        exit()

    branch_dir = os.path.abspath(args.branch_dir)
    dump_dir = os.path.abspath(args.dump_dir)

    # get the language config
    _config_fname = os.path.join(branch_dir, 'languages.yaml')
    with open(_config_fname) as fh:
        _config = yaml.load(fh)
        try:
            lang_config = _config[args.language]
        except KeyError:
            print("ERROR: there's no %r in language config file %r" % (
                  args.language, _config_fname))
            exit()
    logger.info("Opened succesfully language config file %r", _config_fname)

    # get the image type config
    _config_fname = os.path.join(branch_dir, 'imagtypes.yaml')
    with open(_config_fname) as fh:
        _config = yaml.load(fh)
        try:
            imag_config = _config[args.language]
        except KeyError:
            print("ERROR: there's no %r in image type config file %r" % (
                  args.language, _config_fname))
            exit()
    logger.info("Opened succesfully image type config file %r", _config_fname)
    if args.image_type:
        if args.image_type not in imag_config:
            print("ERROR: there's no %r image in the image type config" % (
                  args.image_type))
            exit()

    # branch dir must exist
    if not os.path.exists(branch_dir):
        print("ERROR: The branch dir doesn't exist!")
        exit()

    # fix sys path to branch dir and import the rest of stuff from there
    sys.path.insert(1, branch_dir)
    sys.path.insert(1, os.path.join(branch_dir, "utilities"))
    import list_articles_by_namespaces
    import generar
    from src.scrapping import portals

    # dump dir may not exist, let's just create if it doesn't
    if not os.path.exists(dump_dir):
        os.mkdir(dump_dir)

    main(branch_dir, dump_dir, args.language, lang_config, imag_config,
         nolists=args.no_lists, noscrap=args.no_scrap,
         noclean=args.no_clean, image_type=args.image_type, test=args.test_mode)
