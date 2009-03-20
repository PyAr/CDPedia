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

import config
from src import utiles

class ParseaImagenes(object):
    """
    Tenemos que loguear únicas, ya que tenemos muchísimos, muchísimos
    duplicados: en las pruebas, logueamos 28723 imágenes, que eran 203 únicas!
    """
    def __init__(self):
        self.regex = re.compile('<img(.*?)src="(.*?)"(.*?)/>')
        self.to_log = {}

    def dump(self, dest):
        # guardamos en el log
        with open(dest, "w") as fh:
            info = "\n".join(("%s %s" % x) for x in self.to_log.items())
            fh.write(info + "\n")

    def parsea(self, arch):
        # leemos la info original
        with open(arch) as fh:
            oldhtml = fh.read()

        # sacamos imágenes y reemplazamos paths
        newhtml = self.regex.sub(self._reemplaza, oldhtml)

        # si cambió, lo grabamos nuevamente
        if oldhtml != newhtml:
            with open(arch, "w") as fh:
                fh.write(newhtml)

    def _reemplaza(self, m):
        p1, img, p3 = m.groups()
#        print "img", img

        if img.startswith("../../../../images/shared/thumb"):
            # ../../../../images/shared/thumb/0/0d/Álava.svg/20px-Álava.svg.png
            web_url = "wikipedia/commons/%s" % img[26:]

            partes = img.split("/")
            if len(partes) != 11:
                raise ValueError("Formato de imagen feo! %r" % partes)
            del partes[9]
            dsk_url = "/".join(partes)

        elif img.startswith("../../../../math/"):
            # ../../../../math/5/9/6/596cd268dabd23b450bcbf069f733e4a.png
            web_url = img[12:]
            dsk_url="../../../../images/" + img[12:]

        elif img.startswith("../../../../images/shared"):
            # ../../../../images/shared/b/ba/LocatieZutphen.png
            web_url = "wikipedia/commons/%s" % img[26:]
            dsk_url = img

        elif img.startswith("../../../../images/timeline"):
            # ../../../../images/timeline/8f9a24cab55663baf5110f82ebb97d17.png
            web_url = "wikipedia/es/timeline/%s" % img[27:]
            dsk_url = img

        elif img.startswith("http://upload.wikimedia.org/wikipedia/commons/"):
            # http://upload.wikimedia.org/wikipedia/commons/
            #   thumb/2/22/Heckert_GNU_white.svg/64px-Heckert_GNU_white.svg.png
            web_url = img[27:]

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

        htm_url = '<img%ssrc="%s"%s/>' % (p1, dsk_url, p3)

#        print "web url:", web_url
#        print "htm url:", htm_url
#        print "dsk url:", dsk_url

        # guardamos las imágenes a bajar, y devolvemos lo cambiado para el html
        # le sacamos el "../../../../images/"
        if web_url is not None:
            self.to_log[dsk_url[19:]] = web_url
        return htm_url

def run(verbose):
    def gen():
        fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
        fh.next() # título
        for i,linea in enumerate(fh):
            partes = linea.split()
            arch, dir3 = partes[:2]
            if not arch.endswith(".html"):
                continue

            (categoria, restonom) = utiles.separaNombre(arch)
            if verbose:
                print "Extrayendo imgs de [%d] %s" % (i, arch.encode("utf8"))

            nomreal = os.path.join(config.DIR_PREPROCESADO, dir3, arch)
            yield nomreal

    pi = ParseaImagenes()

    for cant,arch in enumerate(gen()):
        pi.parsea(arch)

    pi.dump(config.LOG_IMAGENES)
    return len(pi.to_log), cant


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit()

    pi = ParseaImagenes()
    pi.parsea(sys.argv[1])
    print "\n".join(str(x) for x in pi.to_log.items())
