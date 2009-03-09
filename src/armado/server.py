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

import cdpindex
import compresor
import config


__version__ = "0.1.1.1.1.1"

reg = re.compile("\<title\>([^\<]*)\</title\>")
reHeader1 = re.compile('\<h1 class="firstHeading"\>([^\<]*)\</h1\>')


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
        print "Cargando template de disco:", nomarch
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

class WikiHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = "WikiServer/" + __version__

    _tpl_mngr = TemplateManager(os.path.join("src", "armado", "templates"))

    _art_mngr = compresor.ArticleManager()

    def do_GET(self):
        """Serve a GET request."""
        tipo, data = self.getfile(self.path)
        if data is not None:
            self.send_response(200)
            #self.send_header("Content-type", tipo)
            self.send_header("Content-Length", len(data))
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

        try:
            data = self._art_mngr.getArticle(path.decode("utf-8"))
        except Exception, e:
            msg = u"Error interno al buscar contenido: %s" % e
            raise ContentNotFound(msg)

        if data is None:
            raise ContentNotFound(
                        u"No se encontró la página '%s'" % path.decode("utf8"))

        return self._arma_pagina(data)

    def _arma_pagina(self, contenido):
        title = getTitleFromData(contenido)
        header = self.templates("header", titulo=title)
        footer = self.templates("footer")
        pag = header + contenido + footer
        return "text/html", pag

    def _main_page(self, msg=u"¡Bienvenido!"):
        pag = self.templates("mainpage", mensaje=msg.encode("utf8"))
        return "text/html", pag

    def getfile(self, path):
        scheme, netloc, path, params, query, fragment = urllib2.urlparse.urlparse(path)
        path = urllib.unquote(path)
        print "get file:", path
        if path == "/index.html":
            return self._main_page()
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

        if path.split("/")[0] in ("images", "raw", "skins", "misc", "extern"):
            asset_file = os.path.join(config.DIR_ASSETS, path)
            asset_data = open(asset_file).read()
            return "image/%s"%path[-3:], asset_data
        if path=="":
            return self._main_page()

        try:
            data = self._get_contenido(path)
        except ContentNotFound, e:
            msg = u"ERROR: '%s' not found (%s)" % (
                                        path.decode("utf8"), e.message)
            return self._main_page(msg)

        return data

    def detallada(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._main_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]

        candidatos = self.index.detailed_search(keywords.decode("utf8"))
        if not candidatos:
            return self._main_page(u"No se encontró nada para lo ingresado!")
        res = []
        for link, titulo, ptje in candidatos:
            linea = '<tr><td><a href="%s">%s</a><small><i>  (%s)</small></i></td></tr> ' % (
                                link.encode("utf8"), titulo.encode("utf8"), ptje)
            res.append(linea)

        pag = self.templates("searchres", results="\n".join(res))
        return "text/html", pag

    def listfull(self, query):
        articulos = self.index.listado_completo()
        res = []
        for link, titulo in articulos:
            linea = '<br/><a href="%s">%s</a>' % (
                                link.encode("utf8"), titulo.encode("utf8"))
            res.append(linea)

        pag = self.templates("listadofull", lineas="\n".join(res))
        return "text/html", pag

    def al_azar(self, query):
        link, tit = self.index.get_random()
        return self._get_contenido(link.encode("utf8"))

    def dosearch(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._main_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]
        candidatos = self.index.search(keywords.decode("utf8"))
        if not candidatos:
            return self._main_page(u"No se encontró nada para lo ingresado!")
        print "==== cand", candidatos
        res = []
        for link, titulo, ptje in candidatos:
            linea = '<tr><td><a href="%s">%s</a></td></tr>' % (
                                link.encode("utf8"), titulo.encode("utf8"))
            res.append(linea)

        pag = self.templates("searchres", results="\n".join(res))
        return "text/html", pag

    def templates(self, nombre_tpl, **kwrds):
        '''Devuelve el texto del template, con la info reemplazada.'''
        t = self._tpl_mngr.get_template(nombre_tpl)
        r = t.substitute(**kwrds)
        return r


def run(event):
    WikiHTTPRequestHandler.index = cdpindex.Index(config.PREFIJO_INDICE)
    WikiHTTPRequestHandler.protocol_version = "HTTP/1.0"
    httpd = BaseHTTPServer.HTTPServer(('', 8000), WikiHTTPRequestHandler)

    print "Sirviendo HTTP en localhost, puerto 8000..."
    event.set()
    httpd.serve_forever()

if __name__ == '__main__':
    run()
