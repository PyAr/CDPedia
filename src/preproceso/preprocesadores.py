#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2006-2017 CDPedistas (see AUTHORS.txt)
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

from __future__ import print_function

import base64
import codecs
import collections
import logging
import os
import re

from urllib2 import unquote

import config

import bs4

SCORE_VIP = 100000000  # 1e8
SCORE_PEISHRANC = 5000

logger = logging.getLogger(__name__)


class _Processor(object):
    """Generic processor, don't use directly, thoght to be subclassed."""

    def __init__(self):
        self.nombre = 'Generic processor'
        self.stats = None

    def __call__(self, wikiarchivo):
        """Aplica el procesador a una instancia de WikiArchivo.

        Ejemplo:
          return (123456, [])
        """
        raise NotImplemented

    def close(self):
        """Close operations, save stuff if needed.

        Overwrite only if necessary.
        """


class ContentExtractor(_Processor):
    """Extract content from the HTML to be used later."""

    # max length of the text extracted from the article
    _max_length = 230

    def __init__(self):
        super(ContentExtractor, self).__init__()
        self.nombre = "ContentExtractor"
        self.output = codecs.open(config.LOG_TITLES, "at", "utf-8")
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        soup = bs4.BeautifulSoup(wikiarchivo.html, "lxml", from_encoding='utf8')

        # extract the title
        node = soup.find('h1')
        if node is None:
            title = u"<no-title>"
            self.stats['title not found'] += 1
        else:
            title = node.text.strip()
            self.stats['title found'] += 1

        # extract the first parragraph
        node = soup.find('p')
        if node is None:
            safe_text = ''
            self.stats['text not found'] += 1
        else:
            text = node.text.strip()
            if len(text) > self._max_length:
                text = text[:self._max_length] + "..."
            safe_text = base64.b64encode(text.encode("utf8"))
            self.stats['text found'] += 1

        # dump to disk
        linea = config.SEPARADOR_COLUMNAS.join((wikiarchivo.url, title, safe_text))
        self.output.write(linea + '\n')
        return (0, [])

    def close(self):
        """Close output."""
        self.output.close()


class VIPDecissor(object):
    """Hold those VIP articles that must be included."""
    def __init__(self):
        self._vip_articles = None

    def _load(self):
        """Load all needed special articles.

        This is done not an __init__ time because some of this are dynamically
        generated files, so doesn't need to happen at import time.
        """
        viparts = self._vip_articles = set()

        # some manually curated pages
        if config.DESTACADOS is not None:
            with codecs.open(config.DESTACADOS, 'rt', encoding='utf8') as fh:
                for line in fh:
                    viparts.add(line.strip())

        # must include according to the config
        viparts.update(config.langconf['include'])

        # those portals articles from the front-page portal
        fname = os.path.join(config.DIR_ASSETS, 'dynamic', 'portals.html')
        if os.path.exists(fname):
            re_link = re.compile(r'<a.*?href="/wiki/(.*?)">', re.MULTILINE | re.DOTALL)
            with open(fname, 'rb') as fh:
                mainpage_portals_content = fh.read()
            for link in re_link.findall(mainpage_portals_content):
                viparts.add(unquote(link).decode('utf8'))
        logger.info("Loaded %d VIP articles", len(viparts))

    def __call__(self, article):
        if self._vip_articles is None:
            self._load()
        return article in self._vip_articles

vip_decissor = VIPDecissor()


class VIPArticles(_Processor):
    """A processor for articles that *must* be included."""
    def __init__(self):
        super(VIPArticles, self).__init__()
        self.nombre = "VIPArticles"
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        if vip_decissor(wikiarchivo.url):
            self.stats['vip'] += 1
            score = SCORE_VIP
        else:
            self.stats['normal'] += 1
            score = 0
        return (score, [])


class OmitirRedirects(_Processor):
    """Procesa y omite de la compilación a los redirects."""
    def __init__(self):
        super(OmitirRedirects, self).__init__()
        self.nombre = "Redirects"
        self.output = codecs.open(config.LOG_REDIRECTS, "a", "utf-8")
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        soup = bs4.BeautifulSoup(wikiarchivo.html, "lxml", from_encoding='utf8')
        node = soup.find('ul', 'redirectText')
        if not node:
            # not a redirect, simple file
            self.stats['simplefile'] += 1
            return (0, [])

        # store the redirect in corresponding file
        self.stats['redirect'] += 1
        url_redirect = node.text
        sep_col = config.SEPARADOR_COLUMNAS
        linea = wikiarchivo.url + sep_col + url_redirect + "\n"
        self.output.write(linea)

        # if redirect was very important, transmit this feature
        # to destination article
        if vip_decissor(wikiarchivo.url):
            trans = [(url_redirect, SCORE_VIP)]
        else:
            trans = []

        # return None for the redirect itself to be discarded
        return (None, trans)

    def close(self):
        """Close output."""
        self.output.close()


class Peishranc(_Processor):
    """Calcula el peishranc.

    Registra las veces que una página es referida por las demás páginas.
    Ignora las auto-referencias y los duplicados.

    NOTA: Si se cambia algo de esta clase, por favor correr los casos de prueba
    en el directorio tests.
    """
    def __init__(self):
        super(Peishranc, self).__init__()
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
                print("ERROR al unquotear/decodear el link", repr(lnk))
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


class Longitud(_Processor):
    """Score the page based on its length (html)."""

    def __init__(self):
        super(Longitud, self).__init__()
        self.nombre = "Longitud"

    def __call__(self, wikiarchivo):
        largo = len(wikiarchivo.html)
        return (largo, [])


class HTMLCleaner(_Processor):
    """Remove different HTML parts or sections."""

    # if the first column found in a link, replace it by its text (keeping stats
    # using the second column)
    unwrap_links = [
        ('redlink', 'redlink'),
        ('action=edit', 'editlinks'),
        ('Especial:Categor', 'category'),
    ]

    def __init__(self):
        super(HTMLCleaner, self).__init__()
        self.nombre = "HTMLCleaner"
        self.stats = collections.Counter()

    def __call__(self, wikiarchivo):
        soup = bs4.BeautifulSoup(wikiarchivo.html, 'lxml', from_encoding='utf8')

        # remove text and links of 'not last version'
        tag = soup.find('div', id='contentSub')
        if tag is not None:
            tag.clear()
            self.stats['notlastversion'] += 1

        # remove edit section
        sections = soup.find_all('span', class_="mw-editsection")
        self.stats['edit_sections'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove ambox (reference needed) section
        sections = soup.find_all('table', class_="ambox")
        self.stats['ambox'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove inline math
        sections = soup.find_all('span', class_="mwe-math-mathml-inline")
        self.stats['inline_math'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove some links (but keeping their text)
        for a_tag in soup.find_all('a'):
            try:
                href = a_tag['href']
            except KeyError:
                # no link
                continue

            for searchable, stat_key in self.unwrap_links:
                if searchable in href:
                    # special link, keep stat and replace it by the text
                    self.stats[stat_key] += 1
                    a_tag.unwrap()
                    break

        # fix original html and return no score at all
        wikiarchivo.html = str(soup)
        return (0, [])


# Clases que serán utilizadas para el preprocesamiento
# de cada una de las páginas, en orden de ejecución.
TODOS = [
    HTMLCleaner,
    VIPArticles,
    OmitirRedirects,
    Peishranc,
    Longitud,
    ContentExtractor,
]
