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

import config
from src.preproceso import preprocesar


class Escalador(object):
    '''Indica en que escala dejar la imágen.'''
    def __init__(self):
        # validamos porcentajes de la config
        porc_escala = [x[1] for x in config.ESCALA_IMAGS]
        if max(porc_escala) != 100 or min(porc_escala) != 0:
            raise ValueError(u"Error en los extremos de config.ESCALA_IMAGS")
        if sorted(porc_escala, reverse=True) != porc_escala:
            raise ValueError(u"Los % de escala no están ordenados")
        if sum(x[0] for x in config.ESCALA_IMAGS) != 100:
            raise ValueError(
                        u"Los % de cant de config.ESCALA_IMAGS no suman 100")

        # preparamos nuestro generador de límites
        vals = []
        base = 0
        for (porc_cant, escala) in config.ESCALA_IMAGS:
            cant = config.LIMITE_PAGINAS * porc_cant / 100
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
    preprocesados = preprocesar.get_top_htmls(config.LIMITE_PAGINAS)
    escalador = Escalador()

    pag_imagenes = {}
    with codecs.open(config.LOG_IMAGPROC, "r", "utf-8") as fh:
        for linea in fh:
            partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dir3 = partes[0]
            fname = partes[1]
            dskurls = partes[2:]
            pag_imagenes[dir3, fname] = dskurls

    escala_imag = {}
    for i, (dir3, fname, _) in enumerate(preprocesados):
        escala = escalador(i)
        if escala == 0:
            continue

        # sacamos qué imágenes le corresponde a este archivo
        dskurls = pag_imagenes[(dir3, fname)]

        # para cada imágen, guardamos el máximo
        for url in dskurls:
            escala_imag[url] = max(escala_imag.get(url, 0), escala)
    del pag_imagenes

    # ya tenemos la escala para todas las imagenes, ahora a relacionarlas
    # con la weburl, y a escribir el log de reduccion

    dskweb = {}
    with codecs.open(config.LOG_IMAGENES, "r", "utf-8") as fh:
        for linea in fh:
            dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dskweb[dsk] = web

    log_reduccion = codecs.open(config.LOG_REDUCCION, "w", "utf8")
    for dskurl, escala in escala_imag.items():
        weburl = dskweb[dskurl]
        info = (str(int(escala)), dskurl, weburl)
        log_reduccion.write(config.SEPARADOR_COLUMNAS.join(info) + "\n")
