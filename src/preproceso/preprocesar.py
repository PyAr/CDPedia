#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, re
import codecs
from os.path import join, abspath, sep, dirname
from urllib2 import urlparse
"""
Uso: preprocesar.py

Aplica los procesadores definidos en config.preprocesadores a cada
una de las páginas, para producir la prioridad con la que página
será (o no) incluída en la compilación.

"""
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
        self.omitir = False
        self.html = open(ruta).read()
        #raise 'ruta: %s, url: %s' % (self.ruta, self.url)
    
    def resethtml(self):
        self.html = open(self.ruta).read()
        return self.html

    def guardar(self):
        destino = self.destino
        if self.ruta == destino:
            raise ValueError, "Intento de guardar el archivo en si mismo"
        
        try: os.makedirs(dirname(destino))
        except os.error: pass
        
        open(destino, 'w').write(self.html)

class WikiSitio:
    def __init__(self, config=None):
        if not config: import config
        self.config = config
        self.ruta = unicode(abspath(config.DIR_RAIZ))
        self.origen = unicode(abspath(config.DIR_RAIZ + sep + config.DIR_A_PROCESAR))
        self.destino = unicode(abspath(config.DIR_PREPROCESADO))
        self.wikiurls = config.USAR_WIKIURLS
        self.resultados = {}
        self.preprocesadores = [ proc(self) for proc in config.PREPROCESADORES ]

    def Archivo(self, ruta):
        return WikiArchivo(self, ruta)
    
    def procesar(self):
        config = self.config
        resultados = self.resultados
        
        for cwd, directorios, archivos in os.walk(self.origen):
            for nombre_archivo in archivos:
                print nombre_archivo.encode("latin1", "replace")
                wikiarchivo = self.Archivo(join(cwd, nombre_archivo))
                url = wikiarchivo.url
                ruta = wikiarchivo.ruta
                resultados.setdefault(url, {})
                
                print 'Procesando: %s' % ruta.encode("latin1", "replace"), repr(url)
                for procesador in self.preprocesadores:
                    resultados[url].setdefault(procesador.nombre, procesador.valor_inicial)
                    procesador(wikiarchivo)
                    if wikiarchivo.omitir: break

                
                if wikiarchivo.omitir:
                    try: del resultados[wikiarchivo.url]
                    except KeyError: pass
                    
                    print '*** Omitido ***'
                    print
                    continue

                print
                wikiarchivo.guardar()
            
        print 'Total: %s páginas' % len(resultados)
        print '***** Fin Procesado *****'

    def guardar(self):
        # Esto se procesa solo si queremos una salida en modo de texto (LOG_PREPROCESADO != None)
        config = self.config
        if config.LOG_PREPROCESADO:
            log = abspath(config.LOG_PREPROCESADO)
            sep_cols = unicode(config.SEPARADOR_COLUMNAS)
            sep_filas = unicode(config.SEPARADOR_FILAS)
            salida = codecs.open(log, "w", "utf-8")

            # Encabezado:
            columnas = [u'Página'] + [procesador.nombre for procesador in self.preprocesadores]
            plantilla = sep_cols.join([u'%s'] * len(columnas)) + sep_filas
            print columnas
            salida.write(plantilla % tuple(columnas))

            # Contenido:
            for pagina, valores in self.resultados.iteritems():
                #los rankings deben ser convertidos en str para evitar literales como 123456L
                columnas = [pagina] + [valores.get(procesador.nombre, procesador.valor_inicial) for procesador in self.preprocesadores]
                salida.write(plantilla % tuple(columnas))
            
            print 'Registro guardado en %s' % log


def run():
    wikisitio = WikiSitio()
    wikisitio.procesar()
    wikisitio.guardar()

if __name__ == "__main__":
    run()
