#!/usr/bin/python
# -*- coding: utf-8 -*-

usage = """
Uso: ExtraerContenido.py

Obtiene la parte relevante de un artículo y crea la lista de redirects "redirects.txt"
"""
import config
import os, re

def getRedirectTarget(html):
    """
    Devuelve la url del destino de un redirect o None si no existe

    """
    match = re.search(r'<meta http-equiv="Refresh" content="\d;url=([^"]+)" />', html)
    if match:
        return match.groups()[0]

def extraerContenido(html):
    """
    Extrae la parte relevante de un artículo

    """
    match = re.search(r'(<h1 class="firstHeading">.+</h1>).*<!-- start content -->\s*(.+)\s*<!-- end content -->', html, re.MULTILINE|re.DOTALL )
    if match:
        return "\n".join(match.groups())


def main(dir):
    redirects_output = open(config.redirects_filename, 'w')
    for dirpath, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            print 'Procesando: %s/%s:' % (dirpath, filename),

            origen_path = os.path.join(dirpath, filename)
            origen = open(origen_path)
            html = origen.read()

            #redirects
            redirect_target = getRedirectTarget(html)
            if redirect_target:
                print "Redirect"
                redirects_output.write("%s %s\n" % (origen_path, redirect_target))
                continue

            #artículos
            newfile = os.path.join(config.dir_recortado, dirpath, filename)
            newpath = os.path.dirname(newfile)
            
            if not os.path.exists(newpath):
                os.makedirs(newpath)
            
            contenido = extraerContenido(html)
            if contenido:
                print "Articulo"
                open(os.path.join(newpath, filename), 'w').write(contenido)
                continue

            #si estamos acá, algo anduvo mal
            raise "Formato de articulo desconocido", origen_path
            

if __name__ == '__main__':
    # import sys
    # if len(sys.argv) != 2:
    #    print usage
    #    sys.exit(1)
    main(config.directorio)