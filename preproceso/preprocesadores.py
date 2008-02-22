#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Funciones para generar los ránkings de las páginas.
Todas reciben como primer argumento "resultados", un diccionario
donde se guardará cada subtotal en una clave propia de la función
que la creó.
El segundo argumento es el html del archivo siendo procesado.
El tercero, es el archivo de configuracion (config.py).
Los restantes argumentos varían, salvo el último que es siempre
**kwargs.

La función debe devolver el conenido de la página (html). Si
devuelve None, se asume que el archivo no debe ser incluído en
la compilación.

Más tarde otra funcion se encargará del algoritmo que produce el
ordenamiento final de las páginas, tomando estos subtotales como
referencia.

"""

from urllib2 import unquote
from urlparse import urljoin

# Procesadores:
def omitir_namespaces(p_nombre, resultados, html, config, nombre_archivo, url_archivo, **kwargs):
    """
    Se omiten las páginas pertenecientes a namespaces terminados de cierta manera.

    """
    if config.buscar_namespaces_omisibles(nombre_archivo):
        print "Omitido (namespace filtrado)"
        open(config.salida_omitido, "a").write(url_archivo + "\n")
        return None #el archivo se omite

    return html

def omitir_redirects(p_nombre, resultados, html, config, url_archivo, **kwargs):
    #redirect:
    match = config.buscar_redirects(html)
    if match:
        print "Redirect"
        open(config.salida_redirects, "a").write("%s %s\n" % (url_archivo, match.groups()[0]))
        return None # el archivo se omite

    return html

def extraer_contenido(p_nombre, resultados, html, config, url_archivo, **kwargs):
    contenido = config.buscar_contenido(html)
    if contenido:
        print "Articulo"
        return "\n".join(contenido.groups())

    #si estamos acá, algo salió mal. Que se sepa.
    raise "Formato de articulo desconocido", url_archivo

def peishranc(p_nombre, p_inicial, resultados, html, config, url_archivo, **kwargs):
    """
    califica las páginas según la cantidad veces que son referidas por otras páginas

    """
    for enlace in config.buscar_enlaces(html):
        url_enlace = urljoin(url_archivo, unquote(enlace))
        print "  *", url_enlace
        r_enlace = resultados.setdefault(url_enlace, {})
        r_enlace[p_nombre] = r_enlace.get(p_nombre, p_inicial) +1
        
    return html

def tamanio(p_nombre, resultados, html, url_archivo, **kwargs):
    """
    califica las páginas según su tamaño

    """
    tamanio = len(html)
    print "-- Tamaño útil: %d --\n" % tamanio
    resultados[url_archivo][p_nombre] = tamanio
    
    return html
