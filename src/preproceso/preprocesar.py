#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uso: preprocesar.py

Aplica los procesadores definidos en config.preprocesadores a cada
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
        self.ruta = ruta = abspath(ruta)

        if not ruta.startswith(wikisitio.ruta):
            raise AttributeError, "%s no pertenece al sitio en %s" % (ruta, wikisitio.ruta)

        # La ruta podría ser algo como 'P:\\cdpedia\\es\\sub\\pagina.html'...
        # Ojo: ruta_relativa *siempre* empieza con '/' (es relativa a la raíz del sitio)
        self.ruta_relativa = ruta_relativa = ruta[len(wikisitio.ruta):]
        self.destino = wikisitio.destino + ruta_relativa
        self.wikisitio = wikisitio
        self.absurl = absurl = urlparse.urljoin('/', '/'.join(ruta_relativa.split(sep)))
        self.pagina = absurl.rsplit('/', 1)[-1]
        #esto podría cambiar (ej. para que sea igual a como está en el sitio):
        self.wikiurl = wikiurl = self.pagina
        self.url = wikisitio.wikiurls and wikiurl or absurl
        self.html = open(ruta).read()
        #raise 'ruta: %s, url: %s' % (self.ruta, self.url)

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
    def __init__(self, dir_raiz, config=None, verbose=False):
        if not config: import config
        self.config = config
        self.ruta = unicode(abspath(dir_raiz))
        self.origen = unicode(abspath(dir_raiz)) # config.DIR_RAIZ + sep + config.DIR_A_PROCESAR))
        self.destino = unicode(abspath(config.DIR_PREPROCESADO))
        self.wikiurls = config.USAR_WIKIURLS
        self.resultados = {}
        self.preprocesadores = [proc(self) for proc in preprocesadores.TODOS]
        self.verbose = verbose

    def Archivo(self, ruta):
        return WikiArchivo(self, ruta)

    def procesar(self):
        config = self.config
        resultados = self.resultados
        puntaje_extra = {}

        for cwd, directorios, archivos in os.walk(self.origen):
            for nombre_archivo in archivos:
                wikiarchivo = self.Archivo(join(cwd, nombre_archivo))
                url = wikiarchivo.url
                if url in resultados:
                    raise ValueError("queloqué?")
#                    resultados.setdefault(url, {})
                resultados[url] = {}

                if self.verbose:
                    print 'Procesando: %s' % url.encode("utf8")
                for procesador in self.preprocesadores:
                    (puntaje, otras_pags) = procesador(wikiarchivo)

                    # None significa que el procesador lo marcó para omitir
                    if puntaje is None:
                        del resultados[url]
                        if self.verbose:
                            print '  omitido!'
                        break

                    # ponemos el puntaje
                    resultados[url][procesador.nombre] = puntaje

                    # agregamos el puntaje extra
                    for extra_pag, extra_ptje in otras_pags:
                        ant = puntaje_extra.setdefault(extra_pag, {})
                        ant[procesador.nombre] = puntaje_extra.get(
                                            procesador.nombre, 0) + extra_ptje
                else:
                    if self.verbose:
                        print "  puntaje:", resultados[url]

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
        config = self.config
        if not config.LOG_PREPROCESADO:
            print "WARNING: no se generó el log porque falta la variable "\
                  "LOG_PREPROCESADO en config.py"
            return

        log = abspath(config.LOG_PREPROCESADO)
        sep_cols = unicode(config.SEPARADOR_COLUMNAS)
        sep_filas = unicode(config.SEPARADOR_FILAS)
        salida = codecs.open(log, "w", "utf-8")

        # Encabezado:
        columnas = [u'Página'] + [p.nombre for p in self.preprocesadores]
        plantilla = sep_cols.join([u'%s'] * len(columnas)) + sep_filas
        salida.write(plantilla % tuple(columnas))

        # Contenido:
        for pagina, valores in self.resultados.iteritems():
            #los rankings deben ser convertidos en str para evitar
            # literales como 123456L
            columnas = [pagina] + [valores.get(p.nombre, p.valor_inicial)
                                                for p in self.preprocesadores]
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
