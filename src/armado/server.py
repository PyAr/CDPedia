# -*- coding: utf-8 -*-
# cdpedia/server.py
"""server"""

from __future__ import division
from __future__ import with_statement

import BaseHTTPServer
import cPickle
import cdpindex
import cgi
import compresor
import config
import operator
import os
import re
import socket
import string
import threading
import time
import urllib   # .quote, .unquote
import urllib2  # .urlparse


__version__ = "0.1.1.1.1.1"

reg = re.compile("\<title\>([^\<]*)\</title\>")
reHeader1 = re.compile('\<h1 class="firstHeading"\>([^\<]*)\</h1\>')

FMT_BUSQ = '<tr><td><a href="%s">%s</a></td></tr> '
RELOAD_HEADER = '<meta http-equiv="refresh" content="2;'\
                'URL=http://localhost:%d/%s">'
BUSQ_NO_RESULTS = u"No se encontró nada para lo ingresado!"


# global variable to hold the port used by the server
serving_port = None


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

NOTFOUND = u"""
El artículo '%s' no pudo ser incluido en el disco <br/><br>
Podés acceder al mismo en Wikipedia en
<a class="external" href="%s">este enlace</a> externo.
"""

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

    def _get_orig_link(self, path):
        """A partir del path devuelve el link original externo."""
        path = path[:-5] # sin el .html

        # veamos si tenemos "_" + cuatro dígitos hexa
        if len(path) > 5 and path[-5] == "_":
            cuad = path[-4:]
            try:
                int(cuad, 16)
            except ValueError:
                pass
            else:
                path = path[:-5]
        orig_link = "http://es.wikipedia.org/wiki/" + path
        return orig_link.decode("utf8")

    def _get_contenido(self, path):
#        print "Get contenido", path
        match = re.match("[^/]+\/[^/]+\/[^/]+\/(.*)", path)
        if match is not None:
            path = match.group(1)

        if path[-4:] != "html":
            raise ContentNotFound(u"Sólo buscamos páginas HTML!")

        orig_link = self._get_orig_link(path)
        try:
            data = self._art_mngr.getArticle(path.decode("utf-8"))
        except Exception, e:
            msg = u"Error interno al buscar contenido: %s" % e
            raise ContentNotFound(msg)

        if data is None:
            m  = NOTFOUND % (path.decode("utf8"), orig_link)
            raise ContentNotFound(m)

        title = getTitleFromData(data)
        return "text/html", self._wrap(data, title, orig_link=orig_link)

    def _wrap(self, contenido, title, orig_link=None):
        header = self.templates("header", titulo=title)

        if orig_link is None:
            orig_link = ""
        else:
            orig_link = u'Puedes visitar la <a class="external" '\
                        u'href="%s">página original aquí</a>' % orig_link

        footer = self.templates("footer", stt_pag=self._stt_pag,
                                stt_img=self._stt_img,
                                orig_link=orig_link.encode("utf8"))
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
        if path == "/buscando":
            return self.buscando(query)
        if path == "/esperando":
            return self._esperando()
        if path == "/dosearch":
            return self.dosearch(query)
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
    def al_azar(self, query):
        link, tit = self.index.get_random()
        return self._get_contenido(link.encode("utf8"))

    @ei.espera_indice
    def dosearch(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._main_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]

        # search in a thread
        buscador.buscar(self.index, keywords.decode("utf8"))
        return self._get_reloading_page(keywords)

    def _get_reloading_page(self, palabras, res_comp=None, res_det=None):
        """Arma la página de recarga."""
        reload = RELOAD_HEADER % (serving_port,
                                  'buscando?pals=' + urllib.quote(palabras))

        aviso = "Buscando: %s %s" % (palabras, "." * buscador.tardando)
        if res_comp is None:
            res_comp = aviso
        if res_det is None:
            res_det = aviso
        pag = self.templates("searchres", results_completa=res_comp,
                             results_detallada=res_det, header=reload)
        return "text/html", self._wrap(pag, "Buscando")

    def buscando(self, query):
        """Muestra resultados cuando terminó de buscar."""
        params = cgi.parse_qs(query)
        palabras = params['pals'][0]

        # si no terminó la primera, devolvemos todo vacío
        if not buscador.done_completa:
            return self._get_reloading_page(palabras)

        # terminó la búsqueda completa
        candidatos = buscador.results_completa
        if candidatos:
            res = []
            cand = sorted(candidatos, key=operator.itemgetter(2), reverse=True)
            for link, titulo, ptje in cand:
                linea = FMT_BUSQ % (link.encode("utf8"), titulo.encode("utf8"))
                res.append(linea)
            results_completa = results="\n".join(res)
        else:
            results_completa = BUSQ_NO_RESULTS.encode("utf8")

        # si no terminó la segunda, devolvemos hasta ahí
        if not buscador.done_detallada:
            return self._get_reloading_page(palabras, results_completa)

        # terminó la búsqueda detallada
        candidatos = buscador.results_detallada
        if candidatos:
            res = []
            cand = sorted(candidatos, key=operator.itemgetter(2), reverse=True)
            for link, titulo, ptje in cand:
                linea = FMT_BUSQ % (link.encode("utf8"), titulo.encode("utf8"))
                res.append(linea)
            results_detallada = results="\n".join(res)
        else:
            results_detallada = BUSQ_NO_RESULTS.encode("utf8")

        pag = self.templates("searchres", results_completa=results_completa,
                             results_detallada=results_detallada, header="")
        return "text/html", self._wrap(pag, "Buscando")

    def templates(self, nombre_tpl, **kwrds):
        '''Devuelve el texto del template, con la info reemplazada.'''
        t = self._tpl_mngr.get_template(nombre_tpl)
        r = t.substitute(**kwrds)
        return r


class Buscador(object):
    def __init__(self):
        self.results_completa = None
        self.results_detallada = None
        self.done_completa = True
        self.done_detallada = True
        self.busqueda = 0
        self._tardando = 0

    @property
    def tardando(self):
        self._tardando += 1
        return self._tardando

    def buscar(self, indice, palabras):
        """Busca en otro thread."""
        self.done_completa = False
        self.done_detallada = False
        self.results = None
        self.busqueda += 1
        self._tardando = 0

        def _inner_completa(nrobusq):
            r = indice.search(palabras)
            if self.busqueda == nrobusq:
                self.results_completa = list(r)
                self.done_completa = True
                threading.Thread(target=_inner_detallada,
                                 args=(self.busqueda,)).start()

        def _inner_detallada(nrobusq):
            r = indice.partial_search(palabras)
            if self.busqueda == nrobusq:
                self.results_detallada = set(r) - set(self.results_completa)
                self.done_detallada = True

        threading.Thread(target=_inner_completa, args=(self.busqueda,)).start()
        return self.busqueda


buscador = Buscador()


def run(event):
    global serving_port

    WikiHTTPRequestHandler.index = cdpindex.IndexInterface(config.DIR_INDICE)
    WikiHTTPRequestHandler.index.start()
    WikiHTTPRequestHandler.protocol_version = "HTTP/1.0"
    for port in xrange(8000, 8099):
        try:
            httpd = BaseHTTPServer.HTTPServer(('', port),
                                              WikiHTTPRequestHandler)
        except socket.error, e:
            if e.errno != 98:
                raise
        else:
            # server opened ok
            serving_port = port
            break

    print "Sirviendo HTTP en localhost, puerto %d..." % port
    event.set()
    httpd.serve_forever()

if __name__ == '__main__':
    run()
