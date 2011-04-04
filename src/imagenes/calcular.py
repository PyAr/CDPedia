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

import codecs
import operator

import config
from src.preproceso import preprocesar


class Escalador(object):
    """Indica en que escala dejar la imagen."""
    def __init__(self, total_items):
        # preparamos nuestro generador de límites
        vals = []
        base = 0
        for (porc_cant, escala) in config.ESCALA_IMAGS:
            cant = total_items * porc_cant / 100
            vals.append((cant + base, escala))
            base += cant

        self.limite = 0
        self.gen_pares = (x for x in vals)

    def __call__(self, nro):
        if nro >= self.limite:
            # pasamos al próximo valor
            (self.limite, self.escala) = self.gen_pares.next()
        return self.escala


def run(verbose):
    # tomar los preprocesador ordenados de más importante a menos
    preprocesados = preprocesar.get_top_htmls()

    # levantamos la relación artículos -> imágenes
    pag_imagenes = {}
    with codecs.open(config.LOG_IMAGPROC, "r", "utf-8") as fh:
        for linea in fh:
            partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dir3 = partes[0]
            fname = partes[1]
            dskurls = partes[2:]
            pag_imagenes[dir3, fname] = dskurls

    # hacemos una lista de las páginas, anotando en que posición la
    # encontramos por primera vez, para luego ordenar por eso (de esta manera,
    # si una misma imagen está en un artículo importante y en otro que no, la
    # imagen va a quedar al 100%)
    imagenes = {}
    for posic_archivo, (dir3, fname, _) in enumerate(preprocesados):
        # sacamos qué imágenes le corresponde a este archivo
        dskurls = pag_imagenes[(dir3, fname)]

        # para cada imagen (si no estaba de antes), guardamos la posición
        # del archivo
        for url in dskurls:
            if url not in imagenes:
                imagenes[url] = posic_archivo

    total_imagenes = len(imagenes)
    imagenes = sorted(imagenes.items(), key=operator.itemgetter(1))

    # levantamos la lista de imágenes para a relacionarlas con la weburl
    dskweb = {}
    with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
        for linea in fh:
            dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dskweb[dsk] = web

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
