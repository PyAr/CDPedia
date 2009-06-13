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
        self.procesados_antes = set()
        if os.path.exists(config.LOG_PREPROCESADO):
            fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
            fh.next() # título
            for linea in fh:
                partes = linea.split(config.SEPARADOR_COLUMNAS)
                arch, dir3, _, _, _, _ = partes
                self.procesados_antes.add((dir3, arch))


    def procesar(self):
        resultados = self.resultados
        puntaje_extra = {}
        de_antes = 0

        for cwd, directorios, archivos in os.walk(self.origen):
            for pag in archivos:
                partes_dir = cwd.split(os.path.sep)
                ult3dirs = join(*partes_dir[-3:])

                # vemos si lo teníamos de antes
                if ((ult3dirs, pag)) in self.procesados_antes:
                    de_antes += 1
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

        return len(resultados), de_antes

    def guardar(self):
        log = abspath(config.LOG_PREPROCESADO)
        preprocs = self.preprocesadores
        sep_cols = unicode(config.SEPARADOR_COLUMNAS)
        plantilla = sep_cols.join([u'%s'] * (len(preprocs) + 2)) + "\n"

        # inicializamos el log (que ya puede estar de antes)
        if os.path.exists(log):
            salida = codecs.open(log, "a", "utf-8")
        else:
            salida = codecs.open(log, "w", "utf-8")

            # encabezado
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

        if self.verbose:
            print 'Registro guardado en %s' % log


def get_top_htmls(limite):
    '''Devuelve los htmls con más puntaje.'''
    # leemos el archivo de preprocesado y calculamos puntaje
    fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
    fh.next() # título
    data = []
    for linea in fh:
        partes = linea.split(config.SEPARADOR_COLUMNAS)
        arch, dir3, _, _, ptj_content, ptj_peishranc = partes
        ptj_content = int(ptj_content)
        ptj_peishranc = int(ptj_peishranc)

        # cálculo de puntaje, mezclando y ponderando los individuales
        puntaje = ptj_content + ptj_peishranc * 5000

        data.append((puntaje, dir3, arch))

    # ordenamos y devolvemos los primeros N
    data.sort(reverse=True)
    data = (x[1:] for x in data[:limite])
    return data

def run(dir_raiz, verbose=False):
    import cProfile
    wikisitio = WikiSitio(dir_raiz, verbose=verbose)
    cantnew, cantold = wikisitio.procesar()
    wikisitio.guardar()
    return cantnew, cantold

if __name__ == "__main__":
    run()
