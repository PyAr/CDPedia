#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Descarga la wikipedia escrapeándola.
"""

from __future__ import with_statement

import os
import sys
import gzip
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
LISTADO_POS_FNAME = "posicion.txt"

UA = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.10) Gecko/20100915 ' \
     'Ubuntu/10.04 (lucid) Firefox/3.6.10'

req = partial(urllib2.Request, data = None,
              headers = {'User-Agent': UA, 'Accept-encoding':'gzip'})

OK, NO_EXISTE, HAY_QUE_PROBAR_DE_NUEVO = range(3)

class URLAlizer(object):
    def __init__(self, listado_nombres, dest_dir):
        self.dest_dir = dest_dir
        try:
            self.posicion_en_listado = int(open(LISTADO_POS_FNAME, "r").readline())
        except IOError:
            self.posicion_en_listado = 0
        self.fh = open(listado_nombres, 'r', buffering=0)
        self.fh.seek(self.posicion_en_listado)
        if self.posicion_en_listado == 0: # saltea la primera linea
            self.fh.readline()

    def _next_name(self):
        return self.fh.readline().decode("utf-8").strip()

    def next(self):
        basename = self._next_name()
        path = os.path.join(self.dest_dir, to3dirs.to_path(basename))
        if not os.path.exists(path.encode('utf-8')):
            os.makedirs(path.encode('utf-8'))

        disk_name = os.path.join(path, to3dirs.to_filename(basename))
        quoted_url = urllib.quote(basename.encode('utf-8'))
        # Skip wikipedia automatic redirect
        url = u"%sw/index.php?title=%s&redirect=no" % (WIKI, quoted_url)
        posicion = self.fh.tell()
        return url, disk_name, self, posicion, basename

    def update_posicion(self, posicion):
        self.posicion_en_listado = posicion

    def __iter__(self):
        return self

def fetch(datos):
    url, disk_name, uralizer, posicion, basename = datos
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

    with open(disk_name.encode("utf-8"), 'w') as fh:
        fh.write(html)

    uralizer.update_posicion(posicion)
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

    with open(LISTADO_POS_FNAME, "w") as fh:
        fh.write(str(urls.posicion_en_listado))

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
  de la conección: latencia, ancho de banda, etc. El default es 20.

  Los nombres de los artículos que no pudieron descargarse correctamente se
  guardan en probar_de_nuevo.txt.

"""

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print USAGE
        sys.exit(1)

    main(*sys.argv[1:])
