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


import logging
import os
import sys
import urllib.parse

import bs4

import config
from src import utiles
from src.armado import to3dirs
from src.preprocessing import preprocess


IMG_URL_PREFIX = config.IMAGES_URL_PREFIX

WIKIPEDIA_URL = "https://{}.wikipedia.org".format(config.LANGUAGE)

# we plainly don't want some images
IMAGES_TO_REMOVE = [
    'Special:CentralAutoLogin',
]

# to get the link after the wiki part
SEPLINK = "/wiki/"

logger = logging.getLogger('images.extract')


class ImageParser:
    """Extract from HTMLs, fix, and log, the URLs of the images.

    The logged URLs are unique (there are a *lot* of duplicated URLs).
    """

    def __init__(self, test=False):
        self.test = test
        self.to_download = {}
        self.process_now = {}
        self.dynamics = {}

        # get which files we processed last time for images and 'nopo' marks
        # (only if the articles are the same, otherwise we need to reprocess
        # everything because of the nopo marks)
        same_before = preprocess.pages_selector.same_info_through_runs
        self.processed_before = {}
        if not test and same_before and os.path.exists(config.LOG_IMAGPROC):
            with open(config.LOG_IMAGPROC, "rt", encoding="utf-8") as fh:
                for line in fh:
                    parts = line.strip().split(config.SEPARADOR_COLUMNAS)
                    dir3 = parts[0]
                    fname = parts[1]
                    dskurls = parts[2:]
                    self.processed_before[dir3, fname] = dskurls
        logger.debug("Records of images processed before: %d",
                     len(self.processed_before))

        # load information of planned downloads
        self.downloads_planned = {}
        if not test and os.path.exists(config.LOG_IMAGENES):
            with open(config.LOG_IMAGENES, "rt", encoding="utf-8") as fh:
                for line in fh:
                    dsk, web = line.strip().split(config.SEPARADOR_COLUMNAS)
                    self.downloads_planned[dsk] = web
        logger.debug("Records of images already planned to download: %d",
                     len(self.downloads_planned))

        self.imgs_ok = 0

        # load included files and its redirections
        sep = config.SEPARADOR_COLUMNAS
        self.chosen_pages = set()
        if not test:
            with open(config.PAG_ELEGIDAS, "rt", encoding="utf-8") as fh:
                self.chosen_pages = set(x.strip().split(sep)[1] for x in fh)
        logger.debug("Quantity of chosen pages, raw: %d",
                     len(self.chosen_pages))

        chpages = self.chosen_pages
        if not test:
            with open(config.LOG_REDIRECTS, "rt", encoding="utf-8") as fh:
                for line in fh:
                    orig, dest = line.strip().split(sep)
                    fname = to3dirs.to_filename(dest)
                    if fname in chpages:
                        chpages.add(orig)
        logger.debug("Quantity of chosen pages, including redirects: %d",
                     len(self.chosen_pages))

    # quantity is how many we have in to_download
    quant = property(lambda s: len(s.to_download))

    def dump(self):
        """Log processed images."""
        separator = config.SEPARADOR_COLUMNAS
        # write the images log
        with open(config.LOG_IMAGENES, "wt", encoding="utf-8") as fh:
            for k, v in self.to_download.items():
                fh.write("%s%s%s\n" % (k, separator, v))

        # rewrite list of walked preprocessed files
        with open(config.LOG_IMAGPROC, "wt", encoding="utf-8") as fh:
            for (dir3, fname), dskurls in self.process_now.items():
                if dskurls:
                    dskurls = separator.join(dskurls)
                    line = separator.join((dir3, fname, dskurls))
                else:
                    line = separator.join((dir3, fname))
                fh.write(line + "\n")
            for name, dskurls in self.dynamics.items():
                dskurls = separator.join(dskurls)
                line = separator.join((config.DYNAMIC, name, dskurls))
                fh.write(line + "\n")

    def parse(self, dir3, fname):
        """Extract and fix image links of preprocessed articles."""
        if (dir3, fname) in self.processed_before:
            prev_dskurls = self.processed_before[dir3, fname]
            self.process_now[dir3, fname] = prev_dskurls
            for dsk_url in prev_dskurls:
                web_url = self.downloads_planned[dsk_url]
                self.to_download[dsk_url] = web_url
                self.imgs_ok += 1
            return

        # read the html from the previous processing step
        arch = os.path.join(config.DIR_PREPROCESADO, dir3, fname)
        with open(arch, "rt", encoding="utf-8") as fh:
            html = fh.read()

        html, newimgs = self.parse_html(html, self.chosen_pages)

        # store the new html
        if not self.test:
            destdir = os.path.join(config.DIR_PAGSLISTAS, dir3)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            newpath = os.path.join(destdir, fname)
            with open(newpath, "wt", encoding="utf-8") as fh:
                fh.write(html)

        # update the images to download
        for dsk, web in newimgs:
            self.to_download[dsk] = web

        # mark the file as processed
        # using dsk_url without the relative path
        imgs = [x[0] for x in newimgs]
        self.process_now[dir3, fname] = imgs

    @staticmethod
    def parse_html(html, chosen_pages):
        """Fix image links of given HTML."""
        soup = bs4.BeautifulSoup(html, "lxml")

        new_images = set()

        for img_tag in soup.find_all('img'):

            dsk_url, web_url = ImageParser.replace(img_tag)
            if dsk_url:
                new_images.add((dsk_url, web_url))

        for a_tag in soup.find_all('a'):
            ImageParser.fixlinks(a_tag, chosen_pages)

        # keep only body content
        soup.html.unwrap()
        soup.body.unwrap()
        html = str(soup)
        return html, new_images

    @staticmethod
    def replace(tag):
        """Replace the img tag in place and return the disk and web urls"""
        img_src = tag.attrs.get("src")

        web_url = 'http:' + img_src

        if img_src.startswith("//upload.wikimedia.org/wikipedia/commons/"):
            parts = img_src[33:].split("/")
            if len(parts) == 6:
                del parts[4]
            elif len(parts) == 4:
                pass
            else:
                raise ValueError("Strange image format! %r" % img_src)

            dsk_url = "/".join(parts)

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
        tag.attrs['src'] = IMG_URL_PREFIX + "%s%s" % (urllib.parse.quote(
                                                      dsk_url.encode("latin-1")), querystr)

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

        # this is a classic article link
        # get filename from link in same format as found in 'chosen_pages'
        if link.startswith(SEPLINK):
            fname = link[len(SEPLINK):]
            # remove fragment part if any
            fname = fname.split("#")[0]
            fname = urllib.parse.unquote(fname)
            fname = to3dirs.to_filename(fname)
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
        tl.log("Parsing found %d images so far (%d of %d pages)", pi.quant, done, total)

    pi.dump()
    return pi.imgs_ok, pi.quant


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
    print("\n".join(str(x) for x in pi.to_download.items()))
