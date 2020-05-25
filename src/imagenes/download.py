# -*- coding: utf8 -*-

# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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

import collections
import logging
import os
import urllib.parse

import config

from src import repartidor, utiles

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
        'Ubuntu/8.10 (intrepid) Firefox/3.0.5')
}

logger = logging.getLogger("images.download")


def _descargar(url, fullpath):
    # descargamos!
    basedir, _ = os.path.split(fullpath)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    req = urllib.request.Request(url.encode("utf8"), headers=HEADERS)
    u = urllib.request.urlopen(req)

    img = u.read()
    with open(fullpath, "wb") as fh:
        fh.write(img)


def descargar(data):
    url, fullpath = data
    retries = 3
    for i in range(retries):
        try:
            _descargar(url, fullpath)
            # todo bien
            return None
        except urllib.error.HTTPError as err:
            # error espeso, devolvemos el código
            return "HTTPError: %d" % (err.code,)
        except Exception as e:
            # algo raro, reintentamos
            print("Uh...", e)
            # demasiados reintentos, devolvemos el último error
            if i == retries - 1:
                return str(e)


def retrieve():
    """Download the images from the net."""
    lista_descargar = []

    # vemos cuales tuvieron problemas antes
    log_errores = os.path.join(config.DIR_TEMP, "imagenes_neterror.txt")
    if os.path.exists(log_errores):
        with open(log_errores, "r", encoding="utf8") as fh:
            imgs_problemas = set(x.strip() for x in fh)
    else:
        imgs_problemas = set()

    for linea in open(config.LOG_REDUCCION, "r", encoding="utf8"):
        linea = linea.strip()
        if not linea:
            continue

        _, arch, url = linea.split(config.SEPARADOR_COLUMNAS)
        fullpath = os.path.join(config.DIR_TEMP, "images", arch)

        if url not in imgs_problemas and not os.path.exists(fullpath):
            lista_descargar.append((url, fullpath))

    tot = len(lista_descargar)
    p = repartidor.Pool(descargar, 5)
    tl = utiles.TimingLogger(30, logger.debug)
    errores = collections.Counter()
    c_ok = 0
    c_err = 0
    for i, result in enumerate(p.procesa(lista_descargar), 1):
        (url, fullpath), stt = result
        if stt is None:
            c_ok += 1
        else:
            errores[stt] += 1
            c_err += 1
            with open(log_errores, "a", encoding="utf8") as fh:
                fh.write(url + "\n")

        tl.log("Downloaded image %d/%d (ok=%d, err=%d)", i, tot, c_ok, c_err)

    for code, cant in errores.most_common():
        logger.warning("Had errors: code=%r quant=%d", code, cant)
