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
import operator

from src.preproceso import preprocesadores

class WikiArchivo:
    def __init__(self, cwd, ult3dirs, nombre_archivo):
        self.ruta_relativa = join(ult3dirs, nombre_archivo)
        self.url = nombre_archivo
        self.html = open(join(cwd, nombre_archivo)).read()

    def guardar(self):
        destino = join(config.DIR_PREPROCESADO, self.ruta_relativa)
        try: os.makedirs(dirname(destino))
        except os.error: pass

        open(destino, 'w').write(self.html)

class WikiSitio(object):
    def __init__(self, dir_raiz, verbose=False):
        self.origen = unicode(abspath(dir_raiz))
        self.resultados = {}
        self.preprocesadores = [proc(self) for proc in preprocesadores.TODOS]
        self.verbose = verbose

        # vemos que habíamos preocesado de antes
        if os.path.exists(config.LOG_PREPROCESADO):
            fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
            fh.next() # título
            procs = [p.nombre for p in self.preprocesadores]
            for linea in fh:
                partes = linea.split(config.SEPARADOR_COLUMNAS)
                arch = partes[0]
                dir3 = partes[1]
                d = {}
                self.resultados[arch] = d
                d["dir3"] = dir3
                for proc, ptje in zip(procs, map(int, partes[2:])):
                    d[proc] = ptje

        # vemos que habíamos descartado antes
        self.descartados = set()
        self._descart = join(config.DIR_TEMP, "descartados.txt")
        if os.path.exists(self._descart):
            fh = codecs.open(self._descart, "r", "utf8")
            for linea in fh:
                self.descartados.add(linea.strip())


    def procesar(self):
        resultados = self.resultados
        puntaje_extra = {}
        de_antes = 0

        for cwd, directorios, archivos in os.walk(self.origen):
            for pag in archivos:
                partes_dir = cwd.split(os.path.sep)
                ult3dirs = join(*partes_dir[-3:])

                # vemos si lo teníamos de antes
                if pag in resultados:
                    de_antes += 1
                    continue
                if pag in self.descartados:
                    continue

                wikiarchivo = WikiArchivo(cwd, ult3dirs, pag)
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
                        self.descartados.add(pag)
                        break

                    # ponemos el puntaje
                    resultados[pag][procesador.nombre] = puntaje

                    # agregamos el puntaje extra
                    for extra_pag, extra_ptje in otras_pags:
                        ant = puntaje_extra.setdefault(extra_pag, {})
                        ant[procesador.nombre] = ant.get(
                                            procesador.nombre, 0) + extra_ptje
                else:
                    if self.verbose:
                        print "  puntaje:", resultados[pag]

                    # lo guardamos sólo si no fue descartado
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

        return len(resultados)-de_antes, de_antes

    def guardar(self):
        log = abspath(config.LOG_PREPROCESADO)
        preprocs = self.preprocesadores
        sep_cols = unicode(config.SEPARADOR_COLUMNAS)
        plantilla = sep_cols.join([u'%s'] * (len(preprocs) + 2)) + "\n"

        # inicializamos el log
        salida = codecs.open(log, "w", "utf-8")
        columnas = [u'Página', u"Dir3"] + [p.nombre for p in preprocs]
        salida.write(plantilla % tuple(columnas))

        # Contenido:
        for pagina, valores in self.resultados.iteritems():
            #los rankings deben ser convertidos en str para evitar
            # literales como 123456L
            columnas = [pagina, valores["dir3"]]
            columnas += [valores.get(p.nombre, p.valor_inicial)
                                                        for p in preprocs]
            salida.write(plantilla % tuple(columnas))

        # descartados
        with codecs.open(self._descart, "w", "utf8") as fh:
            for arch in self.descartados:
                fh.write("%s\n" % arch)

        if self.verbose:
            print 'Registro guardado en %s' % log


def calcula_top_htmls():
    """Calcula los htmls con más puntaje y guarda ambas listas."""
    # leemos el archivo de preprocesado y calculamos puntaje
    fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
    fh.next() # título
    data = []
    for linea in fh:
        partes = linea.split(config.SEPARADOR_COLUMNAS)
        arch, dir3, _, _, _, ptj_content, ptj_peishranc = partes
        ptj_content = int(ptj_content)
        ptj_peishranc = int(ptj_peishranc)

        # cálculo de puntaje, mezclando y ponderando los individuales
        puntaje = ptj_content + ptj_peishranc * 5000

        data.append((dir3, arch, puntaje))

    # ordenamos en función del puntaje
    data.sort(key=operator.itemgetter(2), reverse=True)

    # guardamos los que entran
    with codecs.open(config.PAG_ELEGIDAS, "w", "utf8") as fh:
        for dir3, arch, puntaje in data[:config.LIMITE_PAGINAS]:
            info = (dir3, arch, str(puntaje))
            fh.write(config.SEPARADOR_COLUMNAS.join(info) + "\n")


def get_top_htmls(limite):
    '''Devuelve los htmls con más puntaje.'''
    data = []
    for linea in codecs.open(config.PAG_ELEGIDAS, "r", "utf8"):
        linea = linea.strip()
        dir3, arch, puntaje = linea.split(config.SEPARADOR_COLUMNAS)
        data.append((dir3, arch, int(puntaje)))
    return data


def run(dir_raiz, verbose=False):
#    import cProfile
    wikisitio = WikiSitio(dir_raiz, verbose=verbose)
#    cProfile.runctx("wikisitio.procesar()", globals(), locals(), "/tmp/procesar.stat")
    cantnew, cantold = wikisitio.procesar()
    wikisitio.guardar()
    return cantnew, cantold

if __name__ == "__main__":
    run()
