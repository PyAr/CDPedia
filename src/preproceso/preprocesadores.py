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
import codecs
import collections
import os
import re
import urllib

from urllib2 import unquote

from src import utiles
import config

import bs4

SCORE_DESTACADOS = 100000000  # 1e8
SCORE_PEISHRANC = 5000


class VIPArticle(object):
    """A standalone decissor who knows which articles *must* be included."""

    def __init__(self):
        # store those portals URLs pointed by the home page
        fname = 'resources/static/portales.html'
        link_regex = re.compile(r'<a.*?href="/wiki/(.*?)">',
                                re.MULTILINE | re.DOTALL)
        with open(fname) as fh:
            mainpage_portals_content = fh.read()
        self.portals = set(unquote(link).decode('utf8') for link in
                           link_regex.findall(mainpage_portals_content))

        # destacados FTW!
        self.destacados = [x.strip().decode('utf8')
                           for x in open(config.DESTACADOS)]

    def __call__(self, article):
        # must include according to the config
        if any(article.startswith(fn) for fn in config.INCLUDE):
            return True

        # it's referenced by the portal
        if article in self.portals:
            return True

        # it's included in the custom-made file
        if article in self.destacados:
            return True

        # not really important
        return False

vip_article = VIPArticle()


# Procesadores:
class Procesador(object):
    """Procesador Genérico, no usar directamente."""

    def __init__(self, wikisitio):
        self.nombre = 'Procesador Genérico'
        self.log = None  # ej.: open("archivo.log", "w")
        self.stats = None

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
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        (namespace, restonom) = utiles.separaNombre(wikiarchivo.url)

#        print 'Namespace:', repr(namespace)
        # no da puntaje per se, pero invalida segun namespace
        if namespace is None or config.NAMESPACES.get(namespace) or \
                vip_article(wikiarchivo.url):
#            print '[válido]'
            self.stats['valid'] += 1
            return (0, [])
        else:
#            print '[inválido]'
            self.stats['invalid'] += 1
            return (None, [])


class OmitirRedirects(Procesador):
    """Procesa y omite de la compilación a los redirects."""
    def __init__(self, wikisitio):
        super(OmitirRedirects, self).__init__(wikisitio)
        self.nombre = "Redirects"
        self.log = codecs.open(config.LOG_REDIRECTS, "a", "utf-8")
        regex = r'<span class="redirectText"><a href="/wiki/(.*?)"'
        self.capturar = re.compile(regex).search
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        captura = self.capturar(wikiarchivo.html)
        if not captura:
            # not a redirect, simple file
            self.stats['simplefile'] += 1
            return (0, [])

        # store the redirect in corresponding file
        self.stats['redirect'] += 1
        url_redirect = unquote(captura.groups()[0]).decode("utf-8")
#        print "Redirect %r -> %r" % (wikiarchivo.url, url_redirect)
        sep_col = config.SEPARADOR_COLUMNAS
        linea = wikiarchivo.url + sep_col + url_redirect + "\n"
        self.log.write(linea)

        # if redirect was very important, transmit this feature
        # to destination article
        if vip_article(wikiarchivo.url):
            trans = [(url_redirect, SCORE_DESTACADOS)]
        else:
            trans = []


        # return None for the redirect itself to be discarded
        return (None, trans)


class FixLinksDescartados(Procesador):
    """Corrige los links de lo que descartamos.

    Re-apunta a una página bogus los links que apuntan a un namespace
    que no incluímos.
    """
    def __init__(self, wikisitio):
        super(FixLinksDescartados, self).__init__(wikisitio)
        self.nombre = "FixLinks"
        self.links = re.compile('<a href="(.*?)"(.*?)>(.*?)</a>',
                                re.MULTILINE | re.DOTALL)
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):

        def _reemplaza(m):
            link, relleno, texto = m.groups()

            # si no tiene el ~, no hay nada que ver
            if "%7E" not in link:
                return m.group(0)

            comopath = urllib.url2pathname(link.decode("utf8"))
            base = os.path.basename(comopath)
            categ = base.split("~")[0]

            if config.NAMESPACES.get(categ) or vip_article(base):
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
        indicator = 'intact' if newhtml == wikiarchivo.html else 'modified'
        self.stats[indicator] += 1
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
        self.capturar = re.compile(r'<a href="/wiki/(?P<href>[^"#]*).*?'
                                   r'(?:class="(?P<class>.[^"]*)"|.*?)+>')
        self.stats = collections.Counter()

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
                print "ERROR al unquotear/decodear el link", repr(lnk)
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

        # factor score by constant
        for lnk, score in puntajes.iteritems():
            puntajes[lnk] = score * SCORE_PEISHRANC

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
    """Marca con 1 o 0 si el artículo es destacado o importante.

    En preprocesar.py se le va a dar un montón de puntaje a esto.
    """
    def __init__(self, wikisitio):
        super(Destacado, self).__init__(wikisitio)
        self.nombre = "Destacado"

    def __call__(self, wikiarchivo):
        if vip_article(wikiarchivo.url):
            score = SCORE_DESTACADOS
        else:
            score = 0
        return (score, [])


class HTMLCleaner(Procesador):
    """Remove different HTML parts or sections."""

    _re_category = re.compile(
        '<a.*?title="Especial:Categorías".*?>(?P<texto>.+?)</a>')
    _re_redlink = re.compile(
        '<a href="[^\"]+?&amp;redlink=1".+?>(?P<texto>.+?)</a>')
    _re_edit_links = re.compile(
        '<a href="[^\"]*?action=edit.*?>(?P<texto>.+?)</a>')

    def __init__(self, wikisitio):
        super(HTMLCleaner, self).__init__(wikisitio)
        self.nombre = "HTMLCleaner"
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        html = wikiarchivo.html

        # --- start of soup section (to convert html/soup and back only once)
        soup = bs4.BeautifulSoup(html)

        # remove text and links of 'not last version'
        tag = soup.find('div', id='contentSub')
        if tag is not None:
            tag.clear()
            self.stats['notlastversion'] += 1

        # remove edit section
        edit_sections = soup.find_all('span', class_="mw-editsection")
        self.stats['edit_sections'] += len(edit_sections)
        for tag in edit_sections:
            tag.clear()

        html = str(soup)
        # --- end of soup section

        # remove the "Category", just for aesthetic reasons
        newhtml = self._re_category.sub("\g<texto>", html)
        if newhtml != html:
            self.stats['category'] += 1
        html = newhtml

        # remove the red links (never created in wikipedia) from html
        newhtml = self._re_redlink.sub("\g<texto>", html)
        if newhtml != html:
            self.stats['redlink'] += 1
        html = newhtml

        # remove the edit links
        newhtml = self._re_edit_links.sub("\g<texto>", html)
        if newhtml != html:
            self.stats['editlinks'] += 1
        html = newhtml

        # fix original html and return no score at all
        wikiarchivo.html = html
        return (0, [])


# Clases que serán utilizadas para el preprocesamiento
# de cada una de las páginas, en orden de ejecución.
TODOS = [
    HTMLCleaner,
    Namespaces,
    OmitirRedirects,
    FixLinksDescartados,
    Peishranc,
    Destacado,
    Longitud,
]
