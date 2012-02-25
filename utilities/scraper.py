#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2010-2012 CDPedistas (see AUTHORS.txt)
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
# For further info, check  http://code.google.com/p/cdpedia/

"""Download the whole wikipedia."""

from __future__ import with_statement

import os
import sys
import gzip
import tempfile
import time
import urllib
import StringIO
from functools import partial

import eventlet
from eventlet.green import urllib2

import to3dirs

# Artículos que no se descargaron por alguna razón.
ARTICLES_TO_RETRY = "probar_de_nuevo.txt"

WIKI = 'http://es.wikipedia.org/'

UA = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.10) Gecko/20100915 ' \
     'Ubuntu/10.04 (lucid) Firefox/3.6.10'

req = partial(urllib2.Request, data = None,
              headers = {'User-Agent': UA, 'Accept-encoding':'gzip'})

OK, NO_EXISTE, HAY_QUE_PROBAR_DE_NUEVO = range(3)

class URLAlizer(object):
    def __init__(self, listado_nombres, dest_dir):
        self.dest_dir = dest_dir
        self.temp_dir = dest_dir + ".tmp"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.fh = open(listado_nombres, 'r')

        # saltea la primera linea
        prim_linea = self.fh.readline()
        assert prim_linea.strip() == "page_title"

    def next(self):
        while True:
            line = self.fh.readline()
            if line == "":
                raise StopIteration
            basename = line.decode("utf-8").strip()
            path = os.path.join(self.dest_dir, to3dirs.to_path(basename))
            disk_name = os.path.join(path, to3dirs.to_filename(basename))
            if not os.path.exists(disk_name.encode('utf-8')):
                if not os.path.exists(path.encode('utf-8')):
                    os.makedirs(path.encode('utf-8'))

                temp_file = tempfile.NamedTemporaryFile(suffix=".html",
                              prefix="scrap-", dir=self.temp_dir, delete=False)
                quoted_url = urllib.quote(basename.encode('utf-8'))
                # Skip wikipedia automatic redirect
                url = u"%sw/index.php?title=%s&redirect=no" % (WIKI, quoted_url)
                return url, temp_file, disk_name, self, basename

    def __iter__(self):
        return self

def fetch(datos):
    url, temp_file, disk_name, uralizer, basename = datos
    try:
        response = urllib2.urlopen(req(url))
        compressedstream = StringIO.StringIO(response.read())
        gzipper = gzip.GzipFile(fileobj=compressedstream)
        html = gzipper.read()

    except urllib2.HTTPError, e:
        if e.code == 404:
            return NO_EXISTE, basename
        if e.code == 403:
            return HAY_QUE_PROBAR_DE_NUEVO, basename
        print>>sys.stderr, "%s : %s" % (url, e.code)
        return HAY_QUE_PROBAR_DE_NUEVO, basename
    except Exception, e:
        print>>sys.stderr, "%s : %s" % (url, e)
        return HAY_QUE_PROBAR_DE_NUEVO, basename

    # ok, downloaded the html, let's check that it complies with some rules
    if "</html>" not in html:
        # we surely didn't download it all
        return HAY_QUE_PROBAR_DE_NUEVO, basename
    try:
        html.decode("utf8")
    except UnicodeDecodeError:
        return HAY_QUE_PROBAR_DE_NUEVO, basename

    with temp_file as fh:
        fh.write(html)
    try:
        os.rename(temp_file.name, disk_name.encode("utf-8"))
    except OSError as e:
        print "error creating this file:", disk_name.encode("utf-8")
        return HAY_QUE_PROBAR_DE_NUEVO, basename
    return OK, basename

def main(nombres, dest_dir, pool_size=20):
    pool = eventlet.GreenPool(size=int(pool_size))
    urls = URLAlizer(nombres, dest_dir)

    probar_de_nuevo_file = open(ARTICLES_TO_RETRY, "a", buffering=0)
    total, bien, mal, hay_que_probar_de_nuevo = 0, 0, 0, 0
    tiempo_inicial = time.time()
    try:
        for status, basename in pool.imap(fetch, urls):
            total += 1
            if status == OK:
                bien += 1
            elif status == NO_EXISTE:
                mal += 1
            elif status == HAY_QUE_PROBAR_DE_NUEVO:
                mal += 1
                probar_de_nuevo_file.write(basename.encode("utf-8")+"\n")
                probar_de_nuevo_file.flush()

            velocidad = total/(time.time()-tiempo_inicial)
            sys.stdout.write("\r TOTAL=%d \t BIEN=%d \t MAL=%d \t velocidad = %.2f art/s" %
                             (total, bien, mal, velocidad))
            sys.stdout.flush()

    except (KeyboardInterrupt, SystemExit):
        print "\nStoping, plase wait."

USAGE = """
Usar: scraper.py <NOMBRES_ARTICULOS> <DEST_DIR> [CONCURRENT]"
  Descarga la wikipedia escrapeándola.

  NOMBRES_ARTICULOS es un listado de nombres de artículos. Debe ser descargado
  y descomprimido de:
  http://download.wikipedia.org/eswiki/latest/eswiki-latest-all-titles-in-ns0.gz

  DEST_DIR es el directorio de destino, donde se guardan los artículos. Puede
  ocupar unos 40GB o más.

  CONCURRENT es la cantidad de corrutinas que realizan la descarga. Se puede
  tunear para incrementar velocidad de artículos por segundo. Depende mayormente
  de la conexión: latencia, ancho de banda, etc. El default es 20.

  Los nombres de los artículos que no pudieron descargarse correctamente se
  guardan en probar_de_nuevo.txt.

"""

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print USAGE
        sys.exit(1)

    main(*sys.argv[1:])
