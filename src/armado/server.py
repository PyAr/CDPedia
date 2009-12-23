#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
# cdpedia/server.py
"""server"""

from __future__ import division
from __future__ import with_statement

import BaseHTTPServer
import cgi
import os
import urllib   # .quote, .unquote
import urllib2  # .urlparse
import string
import re
import cPickle
import operator

import cdpindex
import compresor
import config
import time


__version__ = "0.1.1.1.1.1"

reg = re.compile("\<title\>([^\<]*)\</title\>")
reHeader1 = re.compile('\<h1 class="firstHeading"\>([^\<]*)\</h1\>')

FMT_BUSQ = '<tr><td><a href="%s">%s</a></td></tr> '

class ContentNotFound(Exception):
    """No se encontró la página requerida!"""

class TemplateManager(object):
    '''Maneja los templates en disco.'''

    def __init__(self, directorio):
        self.direct = directorio
        self.cache = {}

    def get_template(self, nombre):
        if nombre in self.cache:
            return self.cache[nombre]

        nomarch = os.path.join("src", "armado", "templates", "%s.tpl" % nombre)
#        print "Cargando template de disco:", nomarch
        with open(nomarch, "rb") as f:
            t = string.Template(f.read())

        self.cache[nombre] = t
        return t


def getTitleFromData(data):
    if data is None:
        return ""
    match = reHeader1.search(data)
    if match is not None:
        return match.group(1)
    return ""

def gettitle(zf, name):
    data = open(name).read()
    title_list = reg.findall(data)
    if len(title_list)==1:
        return title_list[0]
    try:
        soup = BeautifulSoup.BeautifulSoup( data )
    except UnicodeEncodeError, e:
        print data
        raise e
    if not soup("title"):
        return ""
    return str(soup("title")[0].contents[0])

def get_stats():
    d = cPickle.load(open(os.path.join(config.DIR_ASSETS, "estad.pkl")))
    pag = "%5d (%2d%%)" % (d['pags_incl'], 100 * d['pags_incl'] / d['pags_total'])
    i_tot = d['imgs_incl'] + d['imgs_bogus']
    img = "%5d (%2d%%)" % (d['imgs_incl'], 100 * d['imgs_incl'] / i_tot)
    return pag, img


# lista para guardar la espera al índice

class EsperaIndice(object):
    def __init__(self):
        self.data_esperando = None
        self.cuanta_espera = ""

    def espera_indice(self, func):
        """Se asegura que el índice esté listo."""
        def _f(*a, **k):
            instancia = a[0]
            if instancia.index.is_ready():
                return func(*a, **k)
            else:
                self.data_esperando = (func, a, k)
                return instancia._index_not_ready()
        return _f

ei = EsperaIndice()

class WikiHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = "WikiServer/" + __version__

    _tpl_mngr = TemplateManager(os.path.join("src", "armado", "templates"))

    _art_mngr = compresor.ArticleManager()

    _stt_pag, _stt_img = get_stats()

    def do_GET(self):
        """Serve a GET request."""
        tipo, data = self.getfile(self.path)
        if data is not None:
            self.send_response(200)
            #self.send_header("Content-type", tipo)
            self.send_header("Content-Length", len(data))
            if tipo != "text/html":
                expiry = self.date_time_string(time.time() + 86400)
                self.send_header("Expires", expiry)
                self.send_header("Cache-Control",
                    "max-age=86400, must-revalidate")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response (404)
            self.end_headers()
            self.wfile.write ("URL not found: %s" % self.path)

    def _get_contenido(self, path):
#        print "Get contenido", path
        match = re.match("[^/]+\/[^/]+\/[^/]+\/(.*)", path)
        if match is not None:
            path = match.group(1)

        if path[-4:] != "html":
            raise ContentNotFound(u"Sólo buscamos páginas HTML!")

        orig_link = "http://es.wikipedia.org/wiki/" + path[:-5] # sin el .html
        try:
            data = self._art_mngr.getArticle(path.decode("utf-8"))
        except Exception, e:
            msg = u"Error interno al buscar contenido: %s" % e
            raise ContentNotFound(msg)

        if data is None:
            m = u"La página '%s' no pudo ser incluida en el disco"
            raise ContentNotFound(m % path.decode("utf8"))

        title = getTitleFromData(data)
        return "text/html", self._wrap(data, title, orig_link=orig_link)

    def _wrap(self, contenido, title, orig_link=None):
        header = self.templates("header", titulo=title)

        if orig_link is None:
            orig_link = ""
        else:
            orig_link = 'Puedes visitar la <a class="external" '\
                        'href="%s">página original aquí</a>' % orig_link

        footer = self.templates("footer", stt_pag=self._stt_pag,
                                stt_img=self._stt_img, orig_link=orig_link)
        return header + contenido + footer


    def _main_page(self, msg=u"¡Bienvenido!"):
        pag = self.templates("mainpage", mensaje=msg.encode("utf8"),
                                stt_pag=self._stt_pag, stt_img=self._stt_img)
        return "text/html", self._wrap(pag, msg.encode("utf8"))

    def _esperando(self):
        """Se fija si debemos seguir esperando o entregamos la data."""
        if self.index.is_ready():
            func, a, k = ei.data_esperando
            return func(*a, **k)
        else:
            ei.cuanta_espera += "."
            return self._index_not_ready()

    def _index_not_ready(self):
        pag = self.templates("indicenolisto", espera=ei.cuanta_espera)
        return "text/html", self._wrap(pag, "por favor, aguarde...")

    def getfile(self, path):
        scheme, netloc, path, params, query, fragment = urllib2.urlparse.urlparse(path)
        path = urllib.unquote(path)
#        print "get file:", path
        if path == "/index.html":
            return self._main_page()
        if path == "/esperando":
            return self._esperando()
        if path == "/dosearch":
            return self.dosearch(query)
        if path == "/detallada":
            return self.detallada(query)
        if path == "/listfull":
            return self.listfull(query)
        if path == "/al_azar":
            return self.al_azar(query)
        if path[0] == "/":
            path = path[1:]

        arranque = path.split("/")[0]

        # los links internos apuntan a algo arrancando con articles, se lo
        # sacamos y tenemos el path que nos sirve
        if arranque == "articles":
            path = path[9:]
            arranque = path.split("/")[0]

        # a todo lo que está afuera de los artículos, en assets, lo tratamos
        # diferente
        if arranque in ("images", "raw", "skins", "misc", "extern"):
            asset_file = os.path.join(config.DIR_ASSETS, path)
            if os.path.exists(asset_file):
                asset_data = open(asset_file, "rb").read()
                return "image/%s"%path[-3:], asset_data
            else:
                print "WARNING: no pudimos encontrar", repr(asset_file)
                return "", ""

        if path=="":
            return self._main_page()

        try:
            data = self._get_contenido(path)
        except ContentNotFound, e:
            return self._main_page(unicode(e))

        return data

    @ei.espera_indice
    def detallada(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._main_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]

        candidatos = self.index.partial_search(keywords.decode("utf8"))
        if not candidatos:
            return self._main_page(u"No se encontró nada para lo ingresado!")
        res = []
        cand = sorted(candidatos, key=operator.itemgetter(2), reverse=True)
        for link, titulo, ptje in cand:
            linea = FMT_BUSQ % (link.encode("utf8"), titulo.encode("utf8"))
            res.append(linea)

        pag = self.templates("searchres", results="\n".join(res))
        return "text/html", self._wrap(pag, "Resultados")

    @ei.espera_indice
    def listfull(self, query):
        articulos = self.index.listado_valores()
        res = []
        for link, titulo in articulos:
            linea = '<a href="%s">%s</a><br/>' % (
                                link.encode("utf8"), titulo.encode("utf8"))
            res.append(linea)

        pag = self.templates("listadofull", lineas="\n".join(res))
        return "text/html", self._wrap(pag, "Listado Completo")

    @ei.espera_indice
    def al_azar(self, query):
        link, tit = self.index.get_random()
        return self._get_contenido(link.encode("utf8"))

    @ei.espera_indice
    def dosearch(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._main_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]
        candidatos = self.index.search(keywords.decode("utf8"))
        if not candidatos:
            return self._main_page(u"No se encontró nada para lo ingresado!")
        res = []
        cand = sorted(candidatos, key=operator.itemgetter(2), reverse=True)
        for link, titulo, ptje in cand:
            linea = FMT_BUSQ % (link.encode("utf8"), titulo.encode("utf8"))
            res.append(linea)

        pag = self.templates("searchres", results="\n".join(res))
        return "text/html", self._wrap(pag, "Resultados")

    def templates(self, nombre_tpl, **kwrds):
        '''Devuelve el texto del template, con la info reemplazada.'''
        t = self._tpl_mngr.get_template(nombre_tpl)
        r = t.substitute(**kwrds)
        return r


def run(event):
    import time
    WikiHTTPRequestHandler.index = cdpindex.IndexInterface(config.DIR_INDICE)
    WikiHTTPRequestHandler.index.start()
    WikiHTTPRequestHandler.protocol_version = "HTTP/1.0"
    httpd = BaseHTTPServer.HTTPServer(('', 8000), WikiHTTPRequestHandler)

    print "Sirviendo HTTP en localhost, puerto 8000..."
    event.set()
    httpd.serve_forever()

if __name__ == '__main__':
    run()
