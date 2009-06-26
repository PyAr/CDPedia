# -*- coding: utf8 -*-

"""
Busca las imágenes en los htmls que están en el archivo de preprocesados, y
convierte las URLs de las mismas para siempre apuntar a disco.

Deja en un log las URLs que hay que bajar (todas aquellas que no deberían ya
venir en el dump).
"""

from __future__ import with_statement

usage = """Extractor de URLs de imágenes.

Para probar el funcionamiento:

  extrae.py dir3 archivo.html
"""

import sys
import re
import os
import codecs
import functools

import config
from src import utiles
from src.preproceso import preprocesar

BOGUS_IMAGE = "../../../extern/sinimagen.png"

class ParseaImagenes(object):
    """
    Tenemos que loguear únicas, ya que tenemos muchísimos, muchísimos
    duplicados: en las pruebas, logueamos 28723 imágenes, que eran 203 únicas!
    """
    def __init__(self, test=False):
        self.test = test
        self.regex = re.compile('<img(.*?)src="(.*?)"(.*?)/>')
        self.a_descargar = {}
        self.proces_ahora = {}

        # levantamos cuales archivos ya habíamos procesado para las imágenes
        self.imag_proc_arch = os.path.join(config.DIR_TEMP, "imag_proc.txt")
        self.proces_antes = {}
        if not test and os.path.exists(self.imag_proc_arch):
            with codecs.open(self.imag_proc_arch, "r", "utf-8") as fh:
                for linea in fh:
                    partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
                    pag = partes[0]
                    bogus = bool(int(partes[1]))
                    dskurls = partes[2:]
                    self.proces_antes[pag] = (bogus, dskurls)

        # levantamos la info de lo planeado a descargar
        self.descarg_antes = {}
        if not test and os.path.exists(config.LOG_IMAGENES):
            with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
                for linea in fh:
                    dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
                    self.descarg_antes[dsk] = web

    # la cantidad es cuantas tenemos en a_descargar
    cant = property(lambda s: len(s.a_descargar))

    def dump(self):
        separador = config.SEPARADOR_COLUMNAS
        # guardar el log de imágenes
        with codecs.open(config.LOG_IMAGENES, "w", "utf-8") as fh:
            for k, v in self.a_descargar.items():
                fh.write("%s%s%s\n" % (k, separador, v))

        # reescribimos todos los preproc que recorrimos
        with codecs.open(self.imag_proc_arch, "w", "utf-8") as fh:
            for pag, (bogus, dskurls) in self.proces_ahora.items():
                if bogus:
                    linea = separador.join((pag, "1"))
                else:
                    if dskurls:
                        dskurls = separador.join(dskurls)
                        linea = separador.join((pag, "0", dskurls))
                    else:
                        linea = separador.join((pag, "0"))
                fh.write(linea + "\n")

    def parsea(self, info, bogus=False):
        dir3, filename = info
        arch = os.path.join(config.DIR_PREPROCESADO, dir3, filename)

        if arch in self.proces_antes:
            prev_bogus, prev_dskurls = self.proces_antes[arch]
            if not prev_bogus and not bogus:
                # procesado antes como real, y ahora también es real
                # no hacemos nada, pero sabemos que las imágenes que
                # tenía van ok
                self.proces_ahora[arch] = (prev_bogus, prev_dskurls)
                for dsk_url in prev_dskurls:
                    web_url = self.descarg_antes[dsk_url]
                    self.a_descargar[dsk_url] = web_url
                return

        # leemos la info original
        with codecs.open(arch, "r", "utf-8") as fh:
            oldhtml = fh.read()

        # sacamos imágenes y reemplazamos paths
        newimgs = []
        reemplaza = functools.partial(self._reemplaza, bogus, newimgs)
        try:
            newhtml = self.regex.sub(reemplaza, oldhtml)
        except Exception, e:
            print "Path del html", arch
            raise e

        # lo grabamos en destino
        if not self.test:
            # verificamos que exista el directorio de destino
            destdir = os.path.join(config.DIR_PAGSLISTAS, dir3)
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            # escribimos el archivo
            newpath = os.path.join(destdir, filename)
            with codecs.open(newpath, "w", "utf-8") as fh:
                fh.write(newhtml)

        # guardamos al archivo como procesado
        if bogus:
            imgs = []
        else:
            # tomamos la dsk_url, sin el path relativo
            imgs = [x[0][19:] for x in newimgs]
        self.proces_ahora[arch] = (bogus, imgs)

        if not bogus:
            # guardamos las imágenes nuevas
            for dsk, web in newimgs:
                # le sacamos el "../../../../images/"
                self.a_descargar[dsk[19:]] = web

    def _reemplaza(self, bogus, newimgs, m):
        p1, img, p3 = m.groups()
        WIKIMEDIA = "http://upload.wikimedia.org/"
        WIKIPEDIA = "http://es.wikipedia.org/"
        if self.test:
            print "img", img

        if img.startswith("../../../../images/shared/thumb"):
            # ../../../../images/shared/thumb/0/0d/Álava.svg/20px-Álava.svg.png
            web_url = WIKIMEDIA + "wikipedia/commons/%s" % img[26:]

            partes = img.split("/")
            if len(partes) != 11:
                raise ValueError("Formato de imagen feo! %r" % partes)
            del partes[9]
            dsk_url = "/".join(partes)

        elif img.startswith("../../../../math/"):
            # ../../../../math/5/9/6/596cd268dabd23b450bcbf069f733e4a.png
            web_url = WIKIMEDIA + img[12:]
            dsk_url="../../../../images/" + img[12:]

        elif img.startswith("../../../../extensions/"):
            web_url = WIKIPEDIA + "w/" + img[12:]
            dsk_url = "../../../../images/" + img[12:]

        elif img.startswith("../../../../images/shared"):
            # ../../../../images/shared/b/ba/LocatieZutphen.png
            web_url = WIKIMEDIA + "wikipedia/commons/%s" % img[26:]
            dsk_url = img

        elif img.startswith("../../../../images/timeline"):
            # ../../../../images/timeline/8f9a24cab55663baf5110f82ebb97d17.png
            web_url = WIKIMEDIA + "wikipedia/es/timeline/%s" % img[27:]
            dsk_url = img

        elif img.startswith("http://upload.wikimedia.org/wikipedia/commons/"):
            # http://upload.wikimedia.org/wikipedia/commons/
            #   thumb/2/22/Heckert_GNU_white.svg/64px-Heckert_GNU_white.svg.png
            web_url = WIKIMEDIA + img[27:]

            partes = img[46:].split("/")
            if len(partes) != 5:
                raise ValueError("Formato de imagen feo! %r" % partes)
            del partes[3]
            dsk_url = "../../../../images/shared/" + "/".join(partes)

        elif img.startswith("../../../../misc") or\
             img.startswith("../../../../skins"):
            # these should be included in the html dump we download
            web_url = None
            dsk_url = img
        else:
            raise ValueError("Formato de imagen no soportado! %r" % img)

        if self.test:
            print "  web url:", web_url
            print "  dsk url:", dsk_url

        # si la imagen a reemplazar no la teníamos de antes, y tampoco
        # es builtin...
        if dsk_url not in self.a_descargar and web_url is not None:
            if bogus:
                # apunta a bogus!
                dsk_url = BOGUS_IMAGE
            else:
                # es útil!
                newimgs.append((dsk_url, web_url))

        # devolvemos lo cambiado para el html
        htm_url = '<img%ssrc="%s"%s/>' % (p1, dsk_url, p3)
        return htm_url

def run(verbose):
    # pedimos LIMITE_PAGINAS porque a todas hay que hacerle algo, ya sea
    # procesar las imágenes o ponerles una bogus
    preprocesados = preprocesar.get_top_htmls(config.LIMITE_PAGINAS)

    pi = ParseaImagenes()

    for info in preprocesados:
        if pi.cant < config.LIMITE_IMAGENES:
            if verbose:
                print "Extrayendo imgs de %s" % info
            pi.parsea(info, bogus=False)
        else:
            if verbose:
                print "Corrigiendo imgs a bogus en %s" % info
            pi.parsea(info, bogus=True)

    pi.dump()
    return pi.cant


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit()

    pi = ParseaImagenes()
    pi.parsea((sys.argv[1], sys.argv[2]))
    print "\n".join(str(x) for x in pi.to_log.items())
