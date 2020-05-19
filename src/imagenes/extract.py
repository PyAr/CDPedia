# -*- coding: utf8 -*-

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

"""Extract images from the HTMLs.

Search the images in the HTMLs located in the preprocessed file and convert
those URLs for them to point to disk.

Also log the URLs that needs to be downloaded.
"""

from __future__ import with_statement, division, print_function

import codecs
import logging
import os
import sys
import urllib
import urllib2

import bs4

import config
from src import utiles
from src.preprocessing import preprocess

IMG_URL_PREFIX = "/images/"

WIKIPEDIA_URL = "https://es.wikipedia.org"

# we plainly don't want some images
IMAGES_TO_REMOVE = [
    'Special:CentralAutoLogin',
]

# to get the link after the wiki part
SEPLINK = "/wiki/"

logger = logging.getLogger(__name__)


class ImageParser(object):
    """Extract from HTMLs, fix, and log, the URLs of the images.

    The logged URLs are unique (there are a *lot* of duplicated URLs).
    """

    def __init__(self, test=False):
        self.test = test
        self.a_descargar = {}
        self.proces_ahora = {}
        self.dynamics = {}

        # get which files we processed last time for images and 'nopo' marks
        # (only if the articles are the same, otherwise we need to reprocess
        # everything because of the nopo marks)
        same_before = preprocess.pages_selector.same_info_through_runs
        self.proces_antes = {}
        if not test and same_before and os.path.exists(config.LOG_IMAGPROC):
            with codecs.open(config.LOG_IMAGPROC, "r", "utf-8") as fh:
                for linea in fh:
                    partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
                    dir3 = partes[0]
                    fname = partes[1]
                    dskurls = partes[2:]
                    self.proces_antes[dir3, fname] = dskurls
        logger.debug("Records of images processed before: %d",
                     len(self.proces_antes))

        # levantamos la info de lo planeado a descargar
        self.descarg_antes = {}
        if not test and os.path.exists(config.LOG_IMAGENES):
            with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
                for linea in fh:
                    dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
                    self.descarg_antes[dsk] = web
        logger.debug("Records of already planned to download: %d",
                     len(self.descarg_antes))

        self.imgs_ok = 0

        # levantamos los archivos que incluimos, y de los redirects a los
        # que incluimos
        sep = config.SEPARADOR_COLUMNAS
        self.pag_elegidas = set()
        if not test:
            with codecs.open(config.PAG_ELEGIDAS, "r", "utf-8") as fh:
                self.pag_elegidas = set(x.strip().split(sep)[1] for x in fh)
        logger.debug("Quantity of chosen pages, raw: %d",
                     len(self.pag_elegidas))

        pageleg = self.pag_elegidas
        if not test:
            with codecs.open(config.LOG_REDIRECTS, "r", "utf-8") as fh:
                for linea in fh:
                    orig, dest = linea.strip().split(sep)
                    if dest in pageleg:
                        pageleg.add(orig)
        logger.debug("Quantity of chosen pages, including redirects: %d",
                     len(self.pag_elegidas))

    # la cantidad es cuantas tenemos en a_descargar
    cant = property(lambda s: len(s.a_descargar))

    def dump(self):
        separador = config.SEPARADOR_COLUMNAS
        # write the images log
        with codecs.open(config.LOG_IMAGENES, "w", "utf-8") as fh:
            for k, v in self.a_descargar.items():
                fh.write("%s%s%s\n" % (k, separador, v))

        # reescribimos todos los preproc que recorrimos
        with codecs.open(config.LOG_IMAGPROC, "w", "utf-8") as fh:
            for (dir3, fname), dskurls in self.proces_ahora.items():
                if dskurls:
                    dskurls = separador.join(dskurls)
                    linea = separador.join((dir3, fname, dskurls))
                else:
                    linea = separador.join((dir3, fname))
                fh.write(linea + "\n")
            for name, dskurls in self.dynamics.items():
                dskurls = separador.join(dskurls)
                linea = separador.join((config.DYNAMIC, name, dskurls))
                fh.write(linea + "\n")

    def process_dynamics(self, name, filepath):
        """Parse a specific special file"""
        if not os.path.exists(filepath):
            logger.warning("Special file not found: %r", filepath)
            return

        with codecs.open(filepath, "rt", encoding="utf8") as fh:
            html = fh.read()

        html, newimgs = self.parse_html(html, self.pag_elegidas)

        with codecs.open(filepath, "wt", "utf-8") as fh:
            fh.write(html)

        for dsk, web in newimgs:
            self.a_descargar[dsk] = web
        self.dynamics[name] = [dsk for dsk, web in newimgs]

    def parse(self, dir3, fname):
        if (dir3, fname) in self.proces_antes:
            prev_dskurls = self.proces_antes[dir3, fname]
            self.proces_ahora[dir3, fname] = prev_dskurls
            for dsk_url in prev_dskurls:
                web_url = self.descarg_antes[dsk_url]
                self.a_descargar[dsk_url] = web_url
                self.imgs_ok += 1
            return

        # read the html from the previous processing step
        arch = os.path.join(config.DIR_PREPROCESADO, dir3, fname)
        with codecs.open(arch, "r", "utf-8") as fh:
            html = fh.read()

        html, newimgs = self.parse_html(html, self.pag_elegidas)

        # store the new html
        if not self.test:
            destdir = os.path.join(config.DIR_PAGSLISTAS, dir3)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            newpath = os.path.join(destdir, fname)
            with codecs.open(newpath, "w", "utf-8") as fh:
                fh.write(html)

        # update the images to download
        for dsk, web in newimgs:
            self.a_descargar[dsk] = web

        # mark the file as processed
        # using dsk_url without the relative path
        imgs = [x[0] for x in newimgs]
        self.proces_ahora[dir3, fname] = imgs

    @staticmethod
    def parse_html(html, chosen_pages):
        soup = bs4.BeautifulSoup(html, "lxml")

        new_images = set()

        for img_tag in soup.find_all('img'):

            dsk_url, web_url = ImageParser.replace(img_tag)
            if dsk_url:
                new_images.add((dsk_url, web_url))

        for a_tag in soup.find_all('a'):
            ImageParser.fixlinks(a_tag, chosen_pages)

        html = unicode(soup)
        return html, new_images

    @staticmethod
    def replace(tag):
        """Replaces the img tag in place and return the disk and web urls"""
        img_src = tag.attrs.get("src")

        web_url = 'http:' + img_src

        if img_src.startswith("//upload.wikimedia.org/wikipedia/commons/"):
            partes = img_src[33:].split("/")
            if len(partes) == 6:
                del partes[4]
            elif len(partes) == 4:
                pass
            else:
                raise ValueError("Strange image format! %r" % img_src)

            dsk_url = "/".join(partes)

        elif img_src.startswith("//bits.wikimedia.org/"):
            dsk_url = img_src[46:]

        elif img_src.startswith("//upload.wikimedia.org/wikipedia/es/"):
            dsk_url = img_src[36:]

        elif img_src.startswith("//upload.wikimedia.org/"):
            dsk_url = img_src[23:]

        elif img_src.startswith("/w/extensions/"):
            web_url = WIKIPEDIA_URL + img_src
            dsk_url = img_src[3:]

        elif img_src.startswith("https://wikimedia.org/api/rest_v1/media/"):
            web_url = img_src
            dsk_url = img_src[40:]

        elif img_src.startswith("/api/rest_v1/page/"):
            web_url = WIKIPEDIA_URL + img_src
            dsk_url = img_src[18:]
        elif any((to_remove in img_src for to_remove in IMAGES_TO_REMOVE)):
            tag.extract()
            return None, None
        else:
            logger.warning("Unsupported image type. Won't be included: %r", img_src)
            return None, None

        # enhance disk paths so they represent the image
        if '/render/svg/' in dsk_url and not dsk_url.lower().endswith('.svg'):
            dsk_url += '.svg'

        if '?' in dsk_url:
            logger.warning("Unsupported image with GET args. Won't be included: %s", dsk_url)
            return None, None

        logger.debug("web url: %r, dsk_url %r", web_url, dsk_url)

        # Replace the width and height by a querystring in the src of the image
        # The idea here is to append the size of the image as a query string.
        # This way we have the information of the real width and height of the image when
        # the request is made so the web server can return a Bogus image if the image was
        # not included in the disk
        img_width, img_height = tag.attrs.pop("width", None), tag.attrs.pop("height", None)
        querystr = '?s=%s-%s' % (img_width, img_height) if img_width and img_height else ''

        # Replace the origial src with the local servable path
        tag.attrs['src'] = IMG_URL_PREFIX + "%s%s" % (urllib.quote(dsk_url.encode("latin-1")),
                                                      querystr)

        tag.attrs.pop("data-file-height", None)
        tag.attrs.pop("data-file-width", None)

        return dsk_url, web_url

    @staticmethod
    def fixlinks(tag, choosen_pages):
        """Multiple postprocesses to the links"""

        # If there is an image inside the <a> tag, we remove the link but leave the child image
        child_img_tag = tag.find("img")
        if child_img_tag:
            tag.replace_with(child_img_tag)
            return

        link = tag.attrs.get('href')

        # Remove the <a> tag if there is no href
        if not link:
            tag.unwrap()
            return

        # this is a  classic article link
        if link.startswith(SEPLINK):
            fname = link[len(SEPLINK):]
            fname = urllib2.unquote(fname)

            # if it was choosen, leave it as is
            if fname not in choosen_pages:
                # mark an unchoosen page with the 'nopo' class
                tag['class'] = tag.get('class', []) + ['nopo']


def run():
    """Extract the images from htmls, and also do extra work on those pages."""
    preprocessed = preprocess.pages_selector.top_pages
    pi = ImageParser()
    total = len(preprocessed)
    logger.info("Image parser inited")

    logger.info("Extract images from special resources.")
    pi.process_dynamics('portals', os.path.join(config.DIR_ASSETS, 'dynamic', 'portals.html'))

    logger.info("Normal pages: %d pages to process", total)
    done = 0
    tl = utiles.TimingLogger(30, logger.debug)

    for dir3, fname, _ in preprocessed:
        try:
            pi.parse(dir3, fname)
        except Exception:
            logger.exception("Parsing crashed in dir3=%r fname=%r", dir3, fname)
            raise

        done += 1
        tl.log("Parsing found %d images so far (%d of %d pages)", pi.cant, done, total)

    pi.dump()
    return pi.imgs_ok, pi.cant


usage = """Images URL extractor.

To test:

  extract.py dir3 somefile.html
"""

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(usage)
        sys.exit()

    # setup logging
    _logger = logging.getLogger()
    handler = logging.StreamHandler()
    _logger.addHandler(handler)
    formatter = logging.Formatter(
        "%(asctime)s  %(name)-15s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    _logger.setLevel(logging.DEBUG)

    preprocess.pages_selector._calculated = True
    pi = ImageParser()
    pi.parse(sys.argv[1], sys.argv[2])
    print("\n".join(str(x) for x in pi.a_descargar.items()))
