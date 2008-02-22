#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, re
from os.path import join, exists

"""
Uso: preprocesar.py

Aplica los procesadores definidos en config.preprocesadores a cada
una de las páginas, para producir la prioridad con la que página
será (o no) incluída en la compilación.

"""

def main(config):
    resultados = {}

    #directorio donde se encuentra la raiz del sitio:
    dir_raiz_letras = len(config.dir_raiz)

    for cwd, directorios, archivos in os.walk(config.dir_origen):
        for nombre_archivo in archivos:
            ruta_archivo = join(cwd, nombre_archivo)
            url_archivo = ruta_archivo[dir_raiz_letras:]
            print 'Procesando: %s' % url_archivo
            html = open(ruta_archivo, 'r').read()

            for pp in config.preprocesadores:
                html = pp(**vars()) #implícito es más corto que explícito...
                if html is None: break

            # Si el html es None, descartamos el archivo
            if html is None:
                try:
                    del resultados[url_archivo]
                except KeyError:
                    pass
                
                print ' *** Omitido ***'
                continue
            
            ruta_dir_destino = join(config.dir_procesado, cwd)
            ruta_archivo_nuevo = join(config.dir_procesado, ruta_archivo)

            if not exists(ruta_dir_destino):
                os.makedirs(ruta_dir_destino)

            open(ruta_archivo_nuevo, 'w').write(html)
            
    # Esto se procesa solo si queremos una salida en modo de texto (salida_ranking != None)
    # actualmente la cantidad de columnas puede variar, habría que considerar implementar csv
    if config.salida_preproceso:
        salida = open(config.salida_preproceso, "w")
        for pagina, valores in resultados.iteritems():
            #los rankings deben ser convertidos en str para evitar literales como 123456L
            columnas = " ".join(str(v) for v in valores.values())
            info = "%s %s\n" % (pagina, columnas)
            salida.write(info)
    print
    print '***** FIN *****'
    return resultados

if __name__ == "__main__":
    import config
    main(config)
