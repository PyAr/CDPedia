#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uso: preprocesar.py

Aplica los procesadores definidos en preprocesadores a cada
una de las páginas, para producir la prioridad con la que página
será (o no) incluída en la compilación.

"""

import os, re
import codecs
from os.path import join, abspath, sep, dirname
from urllib2 import urlparse
import config

from src.preproceso import preprocesadores

class WikiArchivo:
    def __init__(self, wikisitio, ruta):
        self.ruta = ruta

        # Ojo: ruta_relativa *siempre* empieza con '/' (es relativa a la raíz
        # del sitio)
        ruta_relativa = ruta[len(wikisitio.origen):]
        self.destino = config.DIR_PREPROCESADO + ruta_relativa
        self.url = os.path.basename(ruta_relativa)
        self.html = open(ruta).read()

    def resethtml(self):
        self.html = open(self.ruta).read()
        return self.html

    def guardar(self):
        destino = self.destino
        if self.ruta == destino:
            raise ValueError("Intento de guardar el archivo en si mismo")

        try: os.makedirs(dirname(destino))
        except os.error: pass

        open(destino, 'w').write(self.html)

class WikiSitio(object):
    def __init__(self, dir_raiz, verbose=False):
        self.origen = unicode(abspath(dir_raiz))
        self.resultados = {}
        self.preprocesadores = [proc(self) for proc in preprocesadores.TODOS]
        self.verbose = verbose

    def procesar(self):
        resultados = self.resultados
        puntaje_extra = {}

        for cwd, directorios, archivos in os.walk(self.origen):
            for nombre_archivo in archivos:
                wikiarchivo = WikiArchivo(self, join(cwd, nombre_archivo))
                partes_dir = cwd.split(os.path.sep)
                ult3dirs = os.path.join(*partes_dir[-3:])
                pag = wikiarchivo.url
                resultados[pag] = {}
                resultados[pag]["dir3"] = ult3dirs

                if self.verbose:
                    print 'Procesando: %s' % pag.encode("utf8")
                for procesador in self.preprocesadores:
                    (puntaje, otras_pags) = procesador(wikiarchivo)

                    # None significa que el procesador lo marcó para omitir
                    if puntaje is None:
                        del resultados[pag]
                        if self.verbose:
                            print '  omitido!'
                        break

                    # ponemos el puntaje
                    resultados[pag][procesador.nombre] = puntaje

                    # agregamos el puntaje extra
                    for extra_pag, extra_ptje in otras_pags:
                        ant = puntaje_extra.setdefault(extra_pag, {})
                        ant[procesador.nombre] = puntaje_extra.get(
                                            procesador.nombre, 0) + extra_ptje
                else:
                    if self.verbose:
                        print "  puntaje:", resultados[pag]

                wikiarchivo.guardar()
                if self.verbose:
                    print

        # agregamos el puntaje extra sólo si ya teníamos las páginas con nos
        perdidos = []
        for (pag, puntajes) in puntaje_extra.items():
            if pag in resultados:
                for (proc, ptje) in puntajes.items():
                    resultados[pag][proc] += ptje
            else:
                perdidos.append((pag, puntajes))
        if perdidos:
            print "WARNING: Tuvimos %d puntajes perdidos!" % len(perdidos)
#            print perdidos

        return len(resultados)

    def guardar(self):
        # Esto se procesa solo si queremos una salida en modo de texto (LOG_PREPROCESADO != None)
        if not config.LOG_PREPROCESADO:
            print "WARNING: no se generó el log porque falta la variable "\
                  "LOG_PREPROCESADO en config.py"
            return

        log = abspath(config.LOG_PREPROCESADO)
        sep_cols = unicode(config.SEPARADOR_COLUMNAS)
        sep_filas = unicode(config.SEPARADOR_FILAS)
        salida = codecs.open(log, "w", "utf-8")

        # Encabezado:
        preprocs = self.preprocesadores
        columnas = [u'Página', u"Dir3"] + [p.nombre for p in preprocs]
        plantilla = sep_cols.join([u'%s'] * len(columnas)) + sep_filas
        salida.write(plantilla % tuple(columnas))

        # Contenido:
        for pagina, valores in self.resultados.iteritems():
            #los rankings deben ser convertidos en str para evitar
            # literales como 123456L
            columnas = [pagina, valores["dir3"]]
            columnas += [valores.get(p.nombre, p.valor_inicial)
                                                        for p in preprocs]
            salida.write(plantilla % tuple(columnas))

        if self.verbose:
            print 'Registro guardado en %s' % log


def run(dir_raiz, verbose=False):
    wikisitio = WikiSitio(dir_raiz, verbose=verbose)
    cant = wikisitio.procesar()
    wikisitio.guardar()
    return cant

if __name__ == "__main__":
    run()
