#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2006-2012 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  http://code.google.com/p/cdpedia/

"""
Funciones para generar los ránkings de las páginas.
Todas reciben como argumento una WikiPagina.

Más tarde otra funcion se encargará del algoritmo que produce el
ordenamiento final de las páginas, tomando estos subtotales como
referencia.

(facundobatista) Cambié la interacción entre los procesadores y quien
los llama: ahora los procesadores NO tocan el 'resultado' del WikiSitio,
ya que esto hacía que se pierda el control del mismo y aparezcan páginas
espúeras al final.  Ahora cada procesador devuelve dos cosas: el puntaje
de la página que procesa, y una lista de tuplas (otra_página, puntaje) en
caso de asignar puntajes a otras páginas.  En caso de querer omitir la
página que se le ofrece, el procesador debe devolver None en lugar del
puntaje.

"""
from re import compile, MULTILINE, DOTALL
from urllib2 import unquote
import urllib
import codecs
import os

from src import utiles
import config

def mustInclude(filename):
    must = any(filename.startswith(fn) for fn in config.INCLUDE)
    return must

# Procesadores:
class Procesador(object):
    """Procesador Genérico, no usar directamente."""

    def __init__(self, wikisitio):
        self.nombre = 'Procesador Genérico'
        self.log = None # ej.: open("archivo.log", "w")

    def __call__(self, wikiarchivo):
        """Aplica el procesador a una instancia de WikiArchivo.

        Ejemplo:
          return (123456, [])
        """
        raise NotImplemented


class Namespaces(Procesador):
    """Registra el namespace y descarta si el mismo es inválido."""

    def __init__(self, wikisitio):
        super(Namespaces, self).__init__(wikisitio)
        self.nombre = "Namespaces"

    def __call__(self, wikiarchivo):
        (namespace, restonom) = utiles.separaNombre(wikiarchivo.url)

#        print 'Namespace:', repr(namespace)
        # no da puntaje per se, pero invalida segun namespace
        if namespace is None or config.NAMESPACES.get(namespace) or \
            mustInclude(wikiarchivo.url):
#            print '[válido]'
            return (0, [])
        else:
#            print '[inválido]'
            return (None, [])


class OmitirRedirects(Procesador):
    """Procesa y omite de la compilación a los redirects."""
    def __init__(self, wikisitio):
        super(OmitirRedirects, self).__init__(wikisitio)
        self.nombre = "Redirects-"
        self.log = codecs.open(config.LOG_REDIRECTS, "a", "utf-8")
        regex = r'<span class="redirectText"><a href="(.*?)"'
        self.capturar = compile(regex).search

    def __call__(self, wikiarchivo):
        captura = self.capturar(wikiarchivo.html)

        # no da puntaje per se, pero invalida segun namespace
        sep_col = config.SEPARADOR_COLUMNAS
        if captura:
            url_redirect = unquote(captura.groups()[0]).decode("utf-8")
            # le sacamos el /wiki/ del principio
            url_redirect = url_redirect[6:]
#            print "Redirect %r -> %r" % (wikiarchivo.url, url_redirect)
            linea = wikiarchivo.url + sep_col + url_redirect + "\n"
            self.log.write(linea)
            return (None, [])
        else:
            return (0, [])


class FixLinksDescartados(Procesador):
    """Corrige los links de lo que descartamos.

    Re-apunta a una página bogus los links que apuntan a un namespace
    que no incluímos.
    """
    def __init__(self, wikisitio):
        super(FixLinksDescartados, self).__init__(wikisitio)
        self.nombre = "FixLinks"
        self.links = compile('<a href="(.*?)"(.*?)>(.*?)</a>', MULTILINE|DOTALL)

    def __call__(self, wikiarchivo):

        def _reemplaza(m):
            link, relleno, texto = m.groups()

            # si no tiene el ~, no hay nada que ver
            if "%7E" not in link:
                return m.group(0)

            comopath = urllib.url2pathname(link.decode("utf8"))
            base = os.path.basename(comopath)
            categ = base.split("~")[0]

            if config.NAMESPACES.get(categ) or mustInclude(base):
                # está ok, la dejamos intacta
                return m.group(0)

            # sacamos entonces el link
            return texto

        try:
            newhtml = self.links.sub(_reemplaza, wikiarchivo.html)
        except Exception:
            print "Path del html", wikiarchivo.url
            raise

        # reemplazamos el html original
        wikiarchivo.html = newhtml

        # no damos puntaje ni nada
        return (0, [])


class QuitaEditarSpan(Procesador):
    """Quita los [editar] del html."""
    def __init__(self, wikisitio):
        super(QuitaEditarSpan, self).__init__(wikisitio)
        self.nombre = "QuitaEditar"
        self.editar_span = compile('<span class="editsection">.*?</span>', MULTILINE|DOTALL)

    def __call__(self, wikiarchivo):
        try:
            newhtml = self.editar_span.sub("", wikiarchivo.html)
        except Exception:
            print "Path del html", wikiarchivo.url
            raise

        # reemplazamos el html original
        wikiarchivo.html = newhtml

        # no damos puntaje ni nada
        return (0, [])

class QuitaLinksEditar(Procesador):
    """Quita los links que llevan a editar un artículo"""
    def __init__(self, wikisitio):
        super(QuitaLinksEditar, self).__init__(wikisitio)
        self.nombre = "QuitaLinksEditar"
        self.editar_links = compile('<a href="[^\"]*?action=edit.*?>(?P<texto>.+?)</a>')

    def __call__(self, wikiarchivo):
        try:
            newhtml = self.editar_links.sub("\g<texto>", wikiarchivo.html)
        except Exception:
            print "Path del html", wikiarchivo.url
            raise

        # reemplazamops el html original
        wikiarchivo.html = newhtml

        # no damos puntaje ni nada
        return (0, [])

class Peishranc(Procesador):
    """Calcula el peishranc.

    Registra las veces que una página es referida por las demás páginas.
    Ignora las auto-referencias y los duplicados.

    NOTA: Si se cambia algo de esta clase, por favor correr los casos de prueba
    en el directorio tests.
    """
    def __init__(self, wikisitio):
        super(Peishranc, self).__init__(wikisitio)
        self.nombre = "Peishranc"

        # regex preparada por perrito666 y tuute, basicamente matchea todos los
        # href-algo, poniendo href como nombre de grupo de eso que matchea,
        # más un "class=" que es opcional (y poniéndole nombre class);
        self.capturar = compile(r'<a href="/wiki/(?P<href>[^"#]*).*?(?:class="(?P<class>.[^"]*)"|.*?)+>')

    def __call__(self, wikiarchivo):
        puntajes = {}
        for enlace in self.capturar.finditer(wikiarchivo.html):
            data = enlace.groupdict()

            # descartamos por clase y por comienzo del link
            clase = data['class']
            if clase in ('image', 'internal'):
                continue

            # decodificamos y unquoteamos
            lnk = data['href']
            try:
                lnk = unquote(lnk).decode('utf8')
            except UnicodeDecodeError:
                print "ERROR: problemas al unquotear/decodear el link", repr(lnk)
                continue

            namespace, _ = utiles.separaNombre(lnk)
            if namespace is not None and not config.NAMESPACES.get(namespace):
                continue

            # "/" are not really stored like that in disk, they are replaced
            # by the SLASH word
            lnk = lnk.replace("/", "SLASH")

            puntajes[lnk] = puntajes.get(lnk, 0) + 1

        # sacamos el "auto-bombo"
        if wikiarchivo.url in puntajes:
            del puntajes[wikiarchivo.url]

        return (0, puntajes.items())


class Longitud(Procesador):
    """Score the page based on its length (html)."""

    def __init__(self, wikisitio):
        super(Longitud, self).__init__(wikisitio)
        self.nombre = "Longitud"

    def __call__(self, wikiarchivo):
        largo = len(wikiarchivo.html)
        return (largo, [])


class Destacado(Procesador):
    """Marca con puntaje si el artículo es destacado."""
    def __init__(self, wikisitio):
        super(Destacado, self).__init__(wikisitio)
        self.nombre = "Destacado"
        self.destacados = [x.strip().decode('utf8')
                           for x in open(config.DESTACADOS)]

    def __call__(self, wikiarchivo):
        destac = wikiarchivo.url in self.destacados or \
                 mustInclude(wikiarchivo.url)
        return (int(destac), [])


class QuitaCategoria(Procesador):
    """Quita el link de "Categoria" porque es feo"""
    def __init__(self, wikisitio):
        super(QuitaCategoria, self).__init__(wikisitio)
        self.nombre = "QuitaCategoria"
        regex = '<a.*?title="Especial:Categorías".*?>(?P<texto>.+?)</a>'
        self.categoria_regex = compile(regex)

    def __call__(self, wikiarchivo):
        try:
            newhtml = self.categoria_regex.sub("\g<texto>", wikiarchivo.html)
        except Exception:
            print "Path del html", wikiarchivo.url
            raise

        # reemplazamos el html original
        wikiarchivo.html = newhtml

        # no damos puntaje ni nada
        return (0, [])


class QuitaLinkRojo(Procesador):
    """Quita los links rojos (nunca creados en wikipedia) del html."""
    def __init__(self, wikisitio):
        super(QuitaLinkRojo, self).__init__(wikisitio)
        self.nombre = "QuitaLinkRojo"
        regex = '<a href="[^\"]+?&amp;redlink=1".+?>(?P<texto>.+?)</a>'
        self.link_rojo_regex = compile(regex)

    def __call__(self, wikiarchivo):
        try:
            newhtml = self.link_rojo_regex.sub("\g<texto>", wikiarchivo.html)
        except Exception:
            print "Path del html", wikiarchivo.url
            raise

        # reemplazamos el html original
        wikiarchivo.html = newhtml

        # no damos puntaje ni nada
        return (0, [])


# Clases que serán utilizadas para el preprocesamiento
# de cada una de las páginas, en orden de ejecución.
TODOS = [
    Namespaces,
    OmitirRedirects,
    FixLinksDescartados,
    QuitaEditarSpan,
    QuitaLinksEditar,
    QuitaCategoria,
    QuitaLinkRojo,
    Peishranc,
    Destacado,
    Longitud,
]
