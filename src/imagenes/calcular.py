# -*- coding: utf8 -*-

# Copyright 2008-2015 CDPedistas (see AUTHORS.txt)
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

import codecs
import logging
import operator

import config
from src.armado import to3dirs
from src.preproceso import preprocesar

logger = logging.getLogger("images.calculate")

SCALES = (100, 75, 50, 0)

class Escalador(object):
    """Indica en que escala dejar la imagen."""
    def __init__(self, total_items):
        # preparamos nuestro generador de límites
        vals = []
        base = 0
        reduction = config.imageconf['image_reduction']
        logger.info("Reduction: %s", reduction)
        for (porc_cant, escala) in zip(reduction, SCALES):
            cant = total_items * porc_cant / 100
            vals.append((cant + base, escala))
            base += cant
        logger.info("Scales: %s", vals)

        self.limite = 0
        self.gen_pares = (x for x in vals)

    def __call__(self, nro):
        if nro >= self.limite:
            # pasamos al próximo valor
            (self.limite, self.escala) = self.gen_pares.next()
        return self.escala


def run():
    """Calculate the sizes of the images."""
    # levantamos la relación artículos -> imágenes
    pag_imagenes = {}
    dynamics = []
    with codecs.open(config.LOG_IMAGPROC, "r", "utf-8") as fh:
        for linea in fh:
            partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dir3 = partes[0]
            fname = partes[1]
            dskurls = partes[2:]
            if dir3 == config.DYNAMIC:
                dynamics.extend(dskurls)
            else:
                pag_imagenes[dir3, fname] = dskurls

    # hacemos una lista de las páginas, anotando en que posición la
    # encontramos por primera vez, para luego ordenar por eso (de esta manera,
    # si una misma imagen está en un artículo importante y en otro que no, la
    # imagen va a quedar al 100%)
    imagenes = {}
    preprocesados = preprocesar.pages_selector.top_pages
    for posic_archivo, (dir3, fname, _, _) in enumerate(preprocesados):
        # sacamos qué imágenes le corresponde a este archivo
        dskurls = pag_imagenes[(dir3, fname)]

        # para cada imagen (si no estaba de antes), guardamos la posición
        # del archivo
        for url in dskurls:
            if url not in imagenes:
                imagenes[url] = posic_archivo

    # incorporate the dynamic images at the very top
    for url in dynamics:
        imagenes[url] = -1

    total_imagenes = len(imagenes)
    imagenes = sorted(imagenes.items(), key=operator.itemgetter(1))

    # levantamos la lista de imágenes para a relacionarlas con la weburl
    dskweb = {}
    with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
        for linea in fh:
            dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dskweb[dsk] = web

    logger.info("Calculating scales for %d images", total_imagenes)
    escalador = Escalador(total_imagenes)
    log_reduccion = codecs.open(config.LOG_REDUCCION, "w", "utf8")
    for i, (dskurl, _) in enumerate(imagenes):
        escala = escalador(i)
        if escala == 0:
            # ya estamos, no más imágenes
            log_reduccion.close()
            return

        weburl = dskweb[dskurl]
        info = (str(int(escala)), dskurl, weburl)
        log_reduccion.write(config.SEPARADOR_COLUMNAS.join(info) + "\n")
