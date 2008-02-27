#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Funciones para generar los ránkings de las páginas.
Todas reciben como argumento una WikiPagina.

Más tarde otra funcion se encargará del algoritmo que produce el
ordenamiento final de las páginas, tomando estos subtotales como
referencia.

"""
from re import compile, MULTILINE, DOTALL
from urllib2 import unquote
from urlparse import urljoin
import codecs

# Procesadores:
class Procesador(object):
    """
    Procesador Genérico, no usar diréctamente

    """
    def __init__(self, wikisitio):
        """
        Instancia el procesador con los datos necesarios.

        """
        self.valor_inicial = ''
        self.nombre = 'Procesador Genérico'
        self.config = wikisitio.config
        self.resultados = wikisitio.resultados
        self.log = None # ej.: open("archivo.log", "w")
        
    def __call__(self, wikiarchivo):
        """
        Aplica el procesador a una instancia de WikiArchivo.

        """
        # Ejemplo:
        self.resultados[wikiarchivo.url][self.nombre] = 123456


class Namespaces(Procesador):
    """
    Se registra el namespace de la página al mismo tiempo que
    se descartan las páginas de namespaces declarados inválidos.

    """
    def __init__(self, wikisitio):
        super(Namespaces, self).__init__(wikisitio)
        self.nombre = "Namespaces"
        self.log = codecs.open(self.config.LOG_OMITIDO, "w", "utf-8")
        # Deberia dar algo como ".*?(Usuario|Imagen|Discusión|Plantilla)[^~]*~"
        self.regex = r'(%s)~' % '|'.join(self.config.NAMESPACES)
        self.captura_namespace = compile(self.regex).search

        
    def __call__(self, wikiarchivo):
        config = self.config
        captura = self.captura_namespace(wikiarchivo.ruta)
        if captura is None:
            namespace = '' # Namespace Principal
        else:
            namespace = captura.groups()[0]

        print 'Namespace:', namespace or '(Principal)', 
        if namespace in config.NAMESPACES_INVALIDOS:
            print '[ inválido ]'
            self.log.write(wikiarchivo.url + config.SEPARADOR_FILAS)
            wikiarchivo.omitir=True
            return

        print '[ valido ]'
        self.resultados[wikiarchivo.url][self.nombre] = namespace


class OmitirRedirects(Procesador):
    """
    Procesa y omite de la compilación a los redirects

    """
    def __init__(self, wikisitio):
        super(OmitirRedirects, self).__init__(wikisitio)
        self.nombre = "Redirects-"
        self.log = codecs.open(self.config.LOG_REDIRECTS, "w", "utf-8")
        if wikisitio.wikiurls:
            self.regex = r'<meta http-equiv="Refresh" content="\d*;?url=.*?([^/">]+)"'
        else:
            self.regex = r'<meta http-equiv="Refresh" content="\d*;?url=([^">]+)"'

        self.capturar = compile(self.regex).search

    def __call__(self, wikiarchivo):
        config = self.config
        captura = self.capturar(wikiarchivo.html)
        if captura:
            url_redirect = urljoin(wikiarchivo.url, unquote(captura.groups()[0])).decode("utf-8")
            print "Redirect ->", url_redirect.encode("latin1","replace")
            linea = wikiarchivo.url + config.SEPARADOR_COLUMNAS + url_redirect + config.SEPARADOR_FILAS
            self.log.write(linea)
            wikiarchivo.omitir=True


class ExtraerContenido(Procesador):
    """
    Extrae el contenido principal del html de un artículo

    """
    def __init__(self, wikisitio):
        super(ExtraerContenido, self).__init__(wikisitio)
        self.nombre = "Contenido"
        self.valor_inicial = 0
        self.capturar = compile(r'(<h1 class="firstHeading">.+</h1>).*<!-- start content -->\s*(.+)\s*<!-- end content -->', MULTILINE|DOTALL).search
        
    def __call__(self, wikiarchivo):
        # Sólo procesamos html
        if wikiarchivo.url.endswith('.html'):
            html = wikiarchivo.html
            encontrado = self.capturar(html)
            if encontrado:
                print "Articulo -",
                wikiarchivo.html = "\n".join(encontrado.groups())
                tamanio = len(wikiarchivo.html)
                self.resultados[wikiarchivo.url][self.nombre] = tamanio
                print "Tamaño original: %s, Tamaño actual: %s" % (len(html), tamanio)
                
            else:
                # Si estamos acá, el html tiene un formato diferente.
                # Por el momento queremos que se sepa.
                raise ValueError, "El archivo %s posee un formato desconocido" % wikiarchivo.url

class Peishranc(Procesador):
    """
    Registra las veces que una página es referida por las demás páginas.
    Ignora las auto-referencias y los duplicados
    
    """
    def __init__(self, wikisitio):
        super(Peishranc, self).__init__(wikisitio)
        self.nombre = "Peishranc"
        self.valor_inicial = 0
        if wikisitio.wikiurls:
            regex = r'<a\s+[^>]*?href="\.\.\/.*?([^/>"]+\.html)"'
        else:
            regex = r'<a\s+[^>]*?href="(\.\.\/[^">]+\.html)"'
        self.capturar = compile(regex).findall

    def __call__(self, wikiarchivo):
        enlaces = self.capturar(wikiarchivo.html)
        enlaces_vistos = set([wikiarchivo.url])
        if enlaces:
            print "Enlaces:"
            for enlace in enlaces:
                url_enlace = urljoin(wikiarchivo.url, unquote(enlace)).decode("utf-8")
                if not enlace in enlaces_vistos:
                    enlaces_vistos.add(enlace)
                    print "  *", repr(url_enlace)
                    resultado = self.resultados.setdefault(url_enlace, {self.nombre: 0})
                    resultado[self.nombre] += 1


class Longitud(Procesador):
    """
    Califica las páginas según la longitud del contenido (html).
    Actualmente es innecesario si se usa ExtraerContenido, pero es
    hipotéticamente útil si otros (futuros) procesadores alteraran
    el html de forma significativa.
    
    """
    def __init__(self, wikisitio):
        super(Longitud, self).__init__(wikisitio)
        self.nombre = "Longitud"
        self.valor_inicial = 0
        
    def __call__(self, wikiarchivo):
        largo = len(wikiarchivo.html)
        print "-- Tamaño útil: %d --\n" % largo
        self.resultados[wikiarchivo.url][self.nombre] = largo
        
