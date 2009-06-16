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

  extrae.py archivo.html
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
    def __init__(self):
        self.regex = re.compile('<img(.*?)src="(.*?)"(.*?)/>')
        self.to_log = {}

        # levantamos las imágenes ya procesadas
        self.imag_seguro = set()
        self.cant = 0
        if os.path.exists(config.LOG_IMAGENES):
            with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
                for l in fh.readlines():
                    dsk_url, _ = l.split(config.SEPARADOR_COLUMNAS)
                    dsk_url = "../../../../images/" + dsk_url.strip()
                    self.imag_seguro.add(dsk_url)
                    self.cant += 1

        # levantamos cuales archivos ya habíamos procesado para las imágenes
        self.imag_proc = os.path.join(config.DIR_TEMP, "imag_proc.txt")
        self.preproc_recorridos = set()
        if os.path.exists(self.imag_proc):
            with codecs.open(self.imag_proc, "r", "utf-8") as fh:
                for l in fh.readlines():
                    self.preproc_recorridos.add(l.strip())

    def dump(self):
        # appendeamos en el log de imágenes
        with open(config.LOG_IMAGENES, "a") as fh:
            for k, v in self.to_log.items():
                fh.write("%s%s%s\n" % (k, config.SEPARADOR_COLUMNAS, v))

        # reescribimos todos los preproc que recorrimos
        with codecs.open(self.imag_proc, "w", "utf-8") as fh:
            for name in self.preproc_recorridos:
                fh.write(name + "\n")

    def parsea(self, arch, bogus=False):
        if arch in self.preproc_recorridos:
            return

        # leemos la info original
        self.preproc_recorridos.add(arch)
        with open(arch) as fh:
            oldhtml = fh.read()

        # sacamos imágenes y reemplazamos paths
        reemplaza = functools.partial(self._reemplaza, bogus)
        try :
          newhtml = self.regex.sub(reemplaza, oldhtml)
        except Exception,e:
          print "Path del html", arch
          raise e

        # si cambió, lo grabamos nuevamente
        if oldhtml != newhtml:
            with open(arch, "w") as fh:
                fh.write(newhtml)

    def _reemplaza(self, bogus, m):
        p1, img, p3 = m.groups()
        WIKIMEDIA = "http://upload.wikimedia.org/"
        WIKIPEDIA = "http://es.wikipedia.org/"
#        print "img", img

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

        if bogus:
            # si la imagen a reemplazar no la teníamos de antes, bogus!
            if dsk_url not in self.imag_seguro:
                dsk_url = BOGUS_IMAGE

        htm_url = '<img%ssrc="%s"%s/>' % (p1, dsk_url, p3)

#        print "web url:", web_url
#        print "htm url:", htm_url
#        print "dsk url:", dsk_url

        # guardamos las imágenes a bajar, y devolvemos lo cambiado para el html
        # le sacamos el "../../../../images/"
        if web_url is not None and dsk_url not in self.imag_seguro:
            self.to_log[dsk_url[19:]] = web_url
            self.imag_seguro.add(dsk_url)
            self.cant += 1
        return htm_url

def run(verbose):
    def gen():
        # pedimos LIMITE_PAGINAS porque a todas hay que hacerle algo, ya sea
        # procesar las imágenes o ponerles una bogus
        preprocesados = preprocesar.get_top_htmls(config.LIMITE_PAGINAS)

        for i, (dir3, arch) in enumerate(preprocesados):
            (categoria, restonom) = utiles.separaNombre(arch)
            nomreal = os.path.join(config.DIR_PREPROCESADO, dir3, arch)
            yield nomreal

    pi = ParseaImagenes()

    for arch in gen():
        if pi.cant < config.LIMITE_IMAGENES:
            if verbose:
                print "Extrayendo imgs de %s" % arch.encode("utf8")
            pi.parsea(arch)
        else:
            if verbose:
                print "Corrigiendo imgs a bogus en %s" % arch.encode("utf8")
            pi.parsea(arch, bogus=True)

    pi.dump()
    return pi.cant


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit()

    pi = ParseaImagenes()
    pi.parsea(sys.argv[1])
    print "\n".join(str(x) for x in pi.to_log.items())
