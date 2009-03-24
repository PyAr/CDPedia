# -*- coding: utf8 -*-

from __future__ import with_statement

import codecs
import os
import urllib2

import config

HEADERS = {'User-Agent':
    'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
    'Ubuntu/8.10 (intrepid) Firefox/3.0.5'
}

def _descargar(url, fullpath, msg):
    msg("Verificando", repr(fullpath))

    ya_estaba = os.path.exists(fullpath)
    msg("  ", "ya estaba" if ya_estaba else "nop")

    if ya_estaba:
        return

    # descargamos!
    print "Descargando", url
    basedir, _ = os.path.split(fullpath)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    req = urllib2.Request(url.encode("utf8"), headers=HEADERS)
    u = urllib2.urlopen(req)
    largo = int(u.headers["content-length"]) / 1024.0
    msg("  %d KB" % round(largo))

    img = u.read()
    with open(fullpath, "wb") as fh:
        fh.write(img)
    msg("  ok!")


def traer(verbose):
    errores = 0
    for linea in codecs.open(config.LOG_IMAGENES, "r", "utf8"):
        arch, url = linea.split(config.SEPARADOR_COLUMNAS)
        fullpath = os.path.join(config.DIR_TEMP, "images", arch)

        def msg(*t):
            if verbose:
                print " ".join(str(x) for x in t)

        try:
            _descargar(url, fullpath, msg)
        except urllib2.HTTPError, err:
            if err.code == 404:
                msg("  error 404!")
                errores += 1
            else:
                raise
    if errores:
        print "WARNING! Tuvimos %d errores 404" % errores
