# -*- coding: utf8 -*-

"""
Busca las imágenes en los htmls que están en el archivo de preprocesados, y
convierte las URLs de las mismas para siempre apuntar a disco.

Deja en un log las URLs que hay que bajar (todas aquellas que no deberían ya
venir en el dump).
"""

from __future__ import with_statement
from __future__ import division

usage = """Extractor de URLs de imágenes.

Para probar el funcionamiento:

  extrae.py dir3 archivo.html
"""

import sys
import re
import os
import codecs
import functools
import urllib
import urllib2

import config
from src.preproceso import preprocesar

WIKIPEDIA_URL = "http://es.wikipedia.org"

class ParseaImagenes(object):
    """
    Tenemos que loguear únicas, ya que tenemos muchísimos, muchísimos
    duplicados: en las pruebas, logueamos 28723 imágenes, que eran 203 únicas!
    """
    def __init__(self, test=False):
        self.test = test
        self.img_regex = re.compile('<img(.*?)src="(.*?)"(.*?)/>')
        self.anchalt_regex = re.compile('width="(\d+)" height="(\d+)"')
        self.links_regex = re.compile('<a(.*?)href="(.*?)"(.*?)>(.*?)</a>',
                                      re.MULTILINE|re.DOTALL)
        self.seplink = re.compile("/wiki/(.*)")
        self.a_descargar = {}
        self.proces_ahora = {}

        # levantamos cuales archivos ya habíamos procesado para las imágenes
        self.proces_antes = {}
        if not test and os.path.exists(config.LOG_IMAGPROC):
            with codecs.open(config.LOG_IMAGPROC, "r", "utf-8") as fh:
                for linea in fh:
                    partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
                    dir3 = partes[0]
                    fname = partes[1]
                    dskurls = partes[2:]
                    self.proces_antes[dir3, fname] = dskurls

        # levantamos la info de lo planeado a descargar
        self.descarg_antes = {}
        if not test and os.path.exists(config.LOG_IMAGENES):
            with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
                for linea in fh:
                    dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
                    self.descarg_antes[dsk] = web

        self.imgs_ok = 0

        # levantamos los archivos que incluimos, y de los redirects a los
        # que incluimos
        sep = config.SEPARADOR_COLUMNAS
        self.pag_elegidas = set()
        if not test:
            with codecs.open(config.PAG_ELEGIDAS, "r", "utf-8") as fh:
                self.pag_elegidas = set(x.strip().split(sep)[1] for x in fh)

        pageleg = self.pag_elegidas
        if not test:
            with codecs.open(config.LOG_REDIRECTS, "r", "utf-8") as fh:
                for linea in fh:
                    orig, dest = linea.strip().split(sep)
                    if dest in pageleg:
                        pageleg.add(orig)

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

    def parsea(self, dir3, fname):
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
            oldhtml = fh.read()

        # sacamos imágenes y reemplazamos paths
        newimgs = []
        reemplaza = functools.partial(self._reemplaza, newimgs)
        try:
            newhtml = self.img_regex.sub(reemplaza, oldhtml)
        except Exception, e:
            print "Path del html", arch
            raise

        try:
            newhtml = self.links_regex.sub(self._fixlinks, newhtml)
        except Exception:
            print "Path del html", arch
            raise

        # lo grabamos en destino
        if not self.test:
            # verificamos que exista el directorio de destino
            destdir = os.path.join(config.DIR_PAGSLISTAS, dir3)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            # escribimos el archivo
            newpath = os.path.join(destdir, fname)
            with codecs.open(newpath, "w", "utf-8") as fh:
                fh.write(newhtml)

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
        msize = self.anchalt_regex.search(p3)
        p3 = self.anchalt_regex.sub("", p3)
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

        msep = self.seplink.match(link)
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


def run(verbose):
    preprocesados = preprocesar.get_top_htmls()
    pi = ParseaImagenes()

    for dir3, fname, _ in preprocesados:
        if verbose:
            print "Extrayendo imgs de %s/%s" % (dir3.encode("utf8"),
                                                fname.encode("utf8"))
        pi.parsea(dir3, fname)

    pi.dump()
    return pi.imgs_ok, pi.cant


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit()

    pi = ParseaImagenes()
    pi.parsea((sys.argv[1], sys.argv[2]))
    print "\n".join(str(x) for x in pi.to_log.items())
