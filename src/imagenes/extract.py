# -*- coding: utf8 -*-

# Copyright 2008-2014 CDPedistas (see AUTHORS.txt)
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

"""Extract images from the HTMLs.

Search the images in the HTMLs located in the preprocessed file and convert
those URLs for them to point to disk.

Also log the URLs that needs to be downloaded.
"""

from __future__ import with_statement
from __future__ import division

import codecs
import functools
import logging
import os
import re
import sys
import urllib
import urllib2

import config

from src.preproceso import preprocesar

WIKIPEDIA_URL = "http://es.wikipedia.org"

# we plainly don't want some images
IMAGES_TO_REMOVE = re.compile(
    '<img.*?src=".*?/Special:CentralAutoLogin/.*?".*?/>'
)

# to find the images links
IMG_REGEX = re.compile('<img(.*?)src="(.*?)"(.*?)/>')

# to find the pages links
LINKS_REGEX = re.compile('<a (.*?)href="(.*?)"(.*?)>(.*?)</a>',
                         re.MULTILINE|re.DOTALL)

# to get the link after the wiki part
SEPLINK = re.compile("/wiki/(.*)")

# to extracth the sizes of an image
WIDTH_HEIGHT = re.compile('width="(\d+)" height="(\d+)"')

logger = logging.getLogger("extract")


class ImageParser(object):
    """Extract from HTMLs, fix, and log, the URLs of the images.

    The logged URLs are unique (there are a *lot* of duplicated URLs).
    """

    def __init__(self, test=False):
        self.test = test
        self.a_descargar = {}
        self.proces_ahora = {}

        # get which files we processed last time for images and 'nopo' marks
        # (only if the articles are the same, otherwise we need to reprocess
        # everything because of the nopo marks)
        same_before = preprocesar.pages_selector.same_info_through_runs
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
        # guardar el log de imágenes
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

    def parse(self, dir3, fname):
        if (dir3, fname) in self.proces_antes:
            prev_dskurls = self.proces_antes[dir3, fname]
            self.proces_ahora[dir3, fname] = prev_dskurls
            for dsk_url in prev_dskurls:
                web_url = self.descarg_antes[dsk_url]
                self.a_descargar[dsk_url] = web_url
                self.imgs_ok += 1
            return

        # leemos la info original
        arch = os.path.join(config.DIR_PREPROCESADO, dir3, fname)
        with codecs.open(arch, "r", "utf-8") as fh:
            html = fh.read()

        # clean some images that we just don't want
        html = IMAGES_TO_REMOVE.sub("", html)

        # sacamos imágenes y reemplazamos paths
        newimgs = []
        reemplaza = functools.partial(self._reemplaza, newimgs)
        html = IMG_REGEX.sub(reemplaza, html)
        html = LINKS_REGEX.sub(self._fixlinks, html)

        # lo grabamos en destino
        if not self.test:
            # verificamos que exista el directorio de destino
            destdir = os.path.join(config.DIR_PAGSLISTAS, dir3)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            # escribimos el archivo
            newpath = os.path.join(destdir, fname)
            with codecs.open(newpath, "w", "utf-8") as fh:
                fh.write(html)

        # guardamos al archivo como procesado
        # tomamos la dsk_url, sin el path relativo
        imgs = [x[0] for x in newimgs]
        self.proces_ahora[dir3, fname] = imgs

        # guardamos las imágenes nuevas
        for dsk, web in newimgs:
            self.a_descargar[dsk] = web

    def _reemplaza(self, newimgs, m):
        p1, img, p3 = m.groups()
        if self.test:
            print "img", img

        # reemplazamos ancho y alto por un fragment en la URL de la imagen
        msize = WIDTH_HEIGHT.search(p3)
        p3 = WIDTH_HEIGHT.sub("", p3)
        web_url = 'http:' + img

        if img.startswith("//upload.wikimedia.org/wikipedia/commons/"):
            partes = img[33:].split("/")
            if len(partes) == 6:
                del partes[4]
            elif len(partes) == 4:
                pass
            else:
                raise ValueError("Strange image format! %r" % img)

            dsk_url = "/".join(partes)

        elif img.startswith("//bits.wikimedia.org/"):
            dsk_url = img[46:]

        elif img.startswith("//upload.wikimedia.org/wikipedia/es/"):
            dsk_url = img[36:]

        elif img.startswith("//upload.wikimedia.org/"):
            dsk_url = img[23:]

        elif img.startswith("/w/extensions/"):
            web_url = WIKIPEDIA_URL + img
            dsk_url = img[3:]

        else:
            raise ValueError("Unsupported image type! %r" % img)

        if self.test:
            print "  web url:", web_url
            print "  dsk url:", dsk_url

        # si la imagen a reemplazar no la teníamos de antes, y tampoco
        # es builtin...
        if dsk_url not in self.a_descargar and web_url is not None:
            newimgs.append((dsk_url, web_url))
            self.imgs_ok += 1

        if '?' in dsk_url:
            print u"WARNING: Encontramos una URL que ya venía con GET args :("
        # devolvemos lo cambiado para el html
        querystr = ''
        if msize is not None:
            querystr = '?s=%s-%s' % msize.groups()
        htm_url = '<img%ssrc="/images/%s%s"%s/>' % (p1,
            urllib.quote(dsk_url.encode("latin-1")), querystr, p3)
        return htm_url

    def _fixlinks(self, mlink):
        """Pone clase "nopo" a los links que apuntan a algo descartado."""
        relleno_anterior, link, relleno, texto = mlink.groups()
        # Si lo que hay dentro del link es una imagen, devolvemos solo la imagen
        if texto.startswith('<img'):
            return texto

        if link.startswith("http://"):
            return mlink.group()

        msep = SEPLINK.match(link)
        if not msep:
            # un link no clásico, no nos preocupa
            return mlink.group()

        fname = msep.groups()[0]
        fname = urllib2.unquote(fname)
        # los links están en latin1, it sucks!
        fname = fname.encode("latin1").decode("utf8")

        # si la elegimos, joya
        if fname in self.pag_elegidas:
            return mlink.group()

        # sino, la marcamos como "nopo"
        new = '<a class="nopo" %s href="%s"%s>%s</a>' % (relleno_anterior, link, relleno, texto)
        return new


def run():
    """Extract the images from htmls, and also do extra work on those pages."""
    preprocesados = preprocesar.pages_selector.top_pages
    pi = ImageParser()
    total = len(preprocesados)
    logger.info("Image parser inited, %d pages to process", total)

    done = 0
    informed = 0
    for dir3, fname, _ in preprocesados:
        try:
            pi.parse(dir3, fname)
        except:
            logger.warning("Parsing crashed in dir3=%r fname=%r", dir3, fname)
            raise

        # inform if needed
        done += 1
        perc = int(100 * done / total)
        if perc != informed:
            logger.debug("Progress: %d%% done (found so far %d images)",
                         perc, pi.cant)
            informed = perc

    pi.dump()
    return pi.imgs_ok, pi.cant


usage = """Images URL extractor.

To test:

  extract.py dir3 somefile.html
"""

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print usage
        sys.exit()

    # setup logging
    _logger = logging.getLogger()
    handler = logging.StreamHandler()
    _logger.addHandler(handler)
    formatter = logging.Formatter(
        "%(asctime)s  %(name)-15s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    _logger.setLevel(logging.DEBUG)

    preprocesar.pages_selector._calculated = True
    pi = ImageParser()
    pi.parse(sys.argv[1], sys.argv[2])
    print "\n".join(str(x) for x in pi.a_descargar.items())
