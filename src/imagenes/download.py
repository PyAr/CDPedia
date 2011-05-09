# -*- coding: utf8 -*-

from __future__ import with_statement

import codecs
import os
import urllib2

import config
from src import repartidor

HEADERS = {'User-Agent':
    'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
    'Ubuntu/8.10 (intrepid) Firefox/3.0.5'
}

def _descargar(url, fullpath):
    # descargamos!
    basedir, _ = os.path.split(fullpath)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    req = urllib2.Request(url.encode("utf8"), headers=HEADERS)
    u = urllib2.urlopen(req)

    img = u.read()
    with open(fullpath, "wb") as fh:
        fh.write(img)


def descargar(data):
    url, fullpath = data
    for i in range(3):
        try:
            _descargar(url, fullpath)
            # todo bien
            return None
        except urllib2.HTTPError, err:
            # error espeso, devolvemos el código
            return "HTTPError: %d" % (err.code,)
        except Exception, e:
            # algo raro, reintentamos
            print "Uh...", e

    # demasiados reintentos, devolvemos el último error
    return str(e)


def traer(verbose):
    errores = {}
    lista_descargar = []

    # vemos cuales tuvieron problemas antes
    log_errores = os.path.join(config.DIR_TEMP, "imagenes_neterror.txt")
    if os.path.exists(log_errores):
        with codecs.open(log_errores, "r", "utf8") as fh:
            imgs_problemas = set(x.strip() for x in fh)
    else:
        imgs_problemas = set()

    for linea in codecs.open(config.LOG_REDUCCION, "r", "utf8"):
        linea = linea.strip()
        if not linea:
            continue

        _, arch, url = linea.split(config.SEPARADOR_COLUMNAS)
        fullpath = os.path.join(config.DIR_TEMP, "images", arch)

        if url not in imgs_problemas and not os.path.exists(fullpath):
            lista_descargar.append((url, fullpath))

    tot = len(lista_descargar)
    p = repartidor.Pool(descargar, 5)
    for i, result in enumerate(p.procesa(lista_descargar)):
        (url, fullpath), stt = result
        if stt is None:
            stt = "ok"
        else:
            with codecs.open(log_errores, "a", "utf8") as fh:
                fh.write(url + "\n")

        print "   %5d/%d  (%s)  %s" % (i+1, tot, stt, url)

    if errores:
        print "WARNING! Tuvimos errores:"
        for code, cant in errores.items():
            print "       %d %5d" % (code, cant)
