# -*- coding: utf-8 -*-
# cdpedia/server.py
"""server"""

from __future__ import division
from __future__ import with_statement

import cPickle
import cgi
import operator
import os
import re
import socket
import string
import sys
import threading
import time
import urllib   # .quote, .unquote
import urllib2  # .urlparse

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from base64 import b64encode
from mimetypes import guess_type
from random import choice

import bmp
import config
import to3dirs
import cdpindex
import compresor


# En Python 2.5 el SocketServer no tiene un shutdown, así que si estamos
# en esa versión, lo ponemos nosotros (copiado de 2.6, basicamente).

if sys.version_info < (2, 6):
    import select

    class MyHTTPServer(HTTPServer):
        """Version that provides shutdown."""
        def __init__(self, *args, **kwargs):
            HTTPServer.__init__(self, *args, **kwargs)
            self._is_shut_down = threading.Event()
            self._shutdown_request = False

        def serve_forever(self):
            """Handle one request at a time until shutdown."""
            self._is_shut_down.clear()
            try:
                while not self._shutdown_request:
                    r, w, e = select.select([self], [], [], .5)
                    if self not in r:
                        continue
                    try:
                        request, client_address = self.get_request()
                    except socket.error:
                        continue
                    if not self.verify_request(request, client_address):
                        continue

                    try:
                        self.process_request(request, client_address)
                    except:
                        self.handle_error(request, client_address)
                        self.close_request(request)
            finally:
                self._shutdown_request = False
                self._is_shut_down.set()

        def shutdown(self):
            """Stops the serve_forever loop."""
            self._shutdown_request = True
            self._is_shut_down.wait()
else:
    MyHTTPServer = HTTPServer

__version__ = "0.2"

reg = re.compile("\<title\>([^\<]*)\</title\>")
re_header1 = re.compile('\<h1 id="firstHeading" class="firstHeading"\>([^\<]*)\</h1\>')
re_title = re.compile('<title>(.*)</title>')

RELOAD_HEADER = '<meta http-equiv="refresh" content="2;'\
                'URL=http://localhost:%d/%s">'
BUSQ_NO_RESULTS = u"No se encontró nada para lo ingresado!"
LIMPIA = re.compile("[(),]")

WATCHDOG_IFRAME = '<iframe src="/watchdog/update" style="width:1px;height:1px;'\
                  'display:none;"></iframe>'

# variable global para saber el puerto usado por el servidor
serving_port = None

# función para apagar el servidor
shutdown = None

# listado de artículos destacados para mostrar en la mainpage
if config.DESTACADOS:
    destacados = [x.strip().decode('utf8') for x in open(config.DESTACADOS)]
else:
    destacados = None

# construccion con todos los assets usados y lugares para servir data
ALL_ASSETS = config.ASSETS + ["images",  "extern", "tutorial"]
if config.EDICION_ESPECIAL is not None:
    ALL_ASSETS.append(config.EDICION_ESPECIAL)

class ContentNotFound(Exception):
    """No se encontró la página requerida!"""

class ArticleNotFound(ContentNotFound):
    """No se encontró el artículo!"""

class Redirection(Exception):
    """Es una redireccion http"""
    

class InternalServerError(Exception):
    """Error interno al buscar contenido!"""

class TemplateManager(object):
    '''Maneja los templates en disco.'''

    def __init__(self, directorio):
        self.direct = directorio
        self.cache = {}
        if os.path.exists("cdpedia"):
            self.basedir = os.path.join("cdpedia",
                                        "src", "armado", "templates")
        else:
            self.basedir = os.path.join("src", "armado", "templates")

    def get_template(self, nombre):
        if nombre in self.cache:
            return self.cache[nombre]

        nomarch = os.path.join(self.basedir, "%s.tpl" % nombre)
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
    for regexp in (re_header1, re_title):
        match = regexp.search(data)
        if match is not None:
            return match.group(1)
    return ""

def get_stats():
    d = cPickle.load(open(os.path.join(config.DIR_ASSETS, "estad.pkl")))
    pag = "%5d (%2d%%)" % (d['pags_incl'], 100 * d['pags_incl'] / d['pags_total'])
    i_tot = d['imgs_incl'] + d['imgs_bogus']
    if i_tot == 0:
        img = 0
    else:
        img = "%5d (%2d%%)" % (d['imgs_incl'], 100 * d['imgs_incl'] / i_tot)
    return pag, img



class EsperaIndice(object):
    """Lista para guardar la espera al índice."""

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


class WikiHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "WikiServer/" + __version__

    _tpl_mngr = TemplateManager(os.path.join("src", "armado", "templates"))

    _art_mngr = compresor.ArticleManager()

    _img_mngr = compresor.ImageManager()

    _stt_pag, _stt_img = get_stats()

    _portales = open(os.path.join(_tpl_mngr.basedir, "portales.tpl")).read()

    def do_GET(self):
        """Serve a GET request."""
        try:
            tipo, data = self.getfile(self.path)
            self.send_response(200)
            if tipo is not None:
                self.send_header("Content-type", tipo)
            self.send_header("Content-Length", len(data))
            if tipo not in ["text/html", "application/json"]:
                expiry = self.date_time_string(time.time() + 86400)
                self.send_header("Expires", expiry)
                self.send_header("Cache-Control",
                    "max-age=86400, must-revalidate")
            self.end_headers()
            self.wfile.write(data)
        except Redirection, e:
            self.send_response(code=e.args[0])
            self.send_header("Location", e.args[1])
            self.end_headers()
            self.wfile.write(str('redirigiendo'))
        except ArticleNotFound, e:
            self.send_response(code=404)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", len(e.args[0]))
            self.end_headers()
            self.wfile.write(str(e))
        except ContentNotFound, e:
            self.send_error(code=404)
        except InternalServerError, e:
            self.send_error(code=500, message=str(e))

    def _get_orig_link(self, path):
        """A partir del path devuelve el link original externo."""
        orig_link = u"http://es.wikipedia.org/wiki/" + urllib.quote(path.encode("utf-8"))
        return orig_link

    def _get_imagen(self, path, query):
        assert path.startswith('images/')
        try:
            normpath = os.path.normpath(path[len('images/'):])
            asset_data = self._img_mngr.get_item(normpath)
        except Exception, e:
            msg = u"Error interno al buscar contenido: %s" % e
            raise InternalServerError(msg)
        if asset_data is None:
            print "WARNING: no pudimos encontrar", repr(path)
            try:
                width, _, height = query[2:].partition('-')
                width = int(width)
                height = int(height)
            except Exception, e:
                raise ContentNotFound()
            img = bmp.BogusBitMap(width, height)
            return "img/bmp", img.data
        type_ = guess_type(path)[0]
        print "Obtenido", path
        print "Tipo:", type_
        return type_, asset_data

    def _get_contenido(self, path):
        match = re.match("[^/]+\/[^/]+\/[^/]+\/(.*)", path)
        if match is not None:
            path = match.group(1)
        orig_link = self._get_orig_link(path)
        try:
            data = self._art_mngr.get_item(path)
        except Exception, e:
            msg = u"Error interno al buscar contenido: %s" % e
            raise InternalServerError(msg)

        if data is None:
            msg  = NOTFOUND % (path, orig_link)
            raise ArticleNotFound(msg)

        title = getTitleFromData(data)
        return "text/html", self._wrap(data, title, orig_link=orig_link)

    def _wrap(self, contenido, title, orig_link=None):
        header = self.templates("header", titulo=title, iframe=WATCHDOG_IFRAME)

        if orig_link is None:
            orig_link = ""
        else:
            orig_link = u'Si tenés conexión a Internet, podés visitar la '\
                        u'<a class="external" href="%s">página original y '\
                        u'actualizada</a> de éste artículo.'  % orig_link

        footer = self.templates("footer", stt_pag=self._stt_pag,
                                stt_img=self._stt_img,
                                orig_link=orig_link.encode("utf8"))
        return header + contenido + footer

    def _get_destacado(self):
        """Devuelve un destacado... eventualmente."""
        data = None
        while destacados and not data:
            link = choice(destacados)
            data = self._art_mngr.get_item(link)

            if data:
                break

            # destacado roto :|
            print u"WARNING: Artículo destacado no encontrado: %s" % link
            destacados.remove(link)
        else:
            # no hay destacado
            return None

        # La regexp se queda con el título y
        # los párrafos que hay antes de la TOC (si tiene)
        # o antes de la 2da sección
        # Si hay una tabla antes del primer párrafo, la elimina
        # FIXME: Escribir mejor la regex (por lo menos en varias líneas)
        #        o tal vez usar BeautifulSoup
        m = re.search('<h1 id="firstHeading" class="firstHeading">([^<]+).*?<!-- bodytext -->.*?(?:<table .*</table>)?\n(<p>.*?)(?:(?:<table id="toc" class="toc">)|(?:<h2))', data, re.MULTILINE | re.DOTALL)

        if not m:
            print "WARNING: Este articulo rompe la regexp para destacado: %s" % link
            return None

        return link, m.groups()

    def _main_page(self, msg=u"CDPedia v" + config.VERSION):
        """Devuelve la pag principal con destacado y todo."""
        data_destacado = self._get_destacado()
        if data_destacado is not None:
            link, (titulo, primeros_parrafos) = data_destacado
            pag = self.templates("mainpage", mensaje=msg.encode("utf8"),
                                 link=link.encode('utf-8'), titulo=titulo,
                                 primeros_parrafos=primeros_parrafos,
                                 stt_pag=self._stt_pag, stt_img=self._stt_img,
                                 portales=self._portales)
        else:
            pag = self.templates("mainpage_sin_destacado", mensaje=msg.encode("utf8"),
                                 stt_pag=self._stt_pag, stt_img=self._stt_img,
                                 portales=self._portales)
        return "text/html", self._wrap(pag, title="Portada".encode("utf8"))

    def _error_page(self, msg):
        """Devuelve la pag pcipal sin un destacado."""
        pag = self.templates("error_page", mensaje=msg.encode("utf8"),
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
        if path == "/":
            return self._main_page()
        if path == "/buscando":
            return self.buscando(query)
        if path == "/esperando":
            return self._esperando()
        if path == "/dosearch":
            return self.dosearch(query)
        if path == "/ajax/index/ready":
            return self.ajax_index_ready()
        if path == "/ajax/buscar":
            return self.ajax_search(query)
        if path == "/ajax/buscar/resultado":
            return self.ajax_search_get_results()
        if path == "/watchdog/update":
            return self.watchdog_update()
        if path == "/al_azar":
            return self.al_azar(query)
        if path[0] == "/":
            path = path[1:]

        arranque = path.split("/")[0]

        # los links internos apuntan a algo arrancando con wiki, se lo
        # sacamos y tenemos el path que nos sirve
        if arranque == "wiki":
            articulo = path[len("wiki/"):].decode("utf-8")
            if articulo:
                path = to3dirs.to_complete_path(articulo)

        # las páginas de 'institucional' están hechas a mano, pero van
        # insertadas en el marco normal
        elif arranque == "institucional":
            return self.institucional(path)

        # Las imagenes las buscamos de bloques:
        elif arranque == 'images':
            return self._get_imagen(path, query)

        # a todo lo que está afuera de los artículos, en assets, lo tratamos
        # diferente
        elif arranque in ALL_ASSETS:
            asset_file = os.path.join(config.DIR_ASSETS, path)
            if os.path.isdir(asset_file):
                print "WARNING: ", repr(asset_file), "es un directorio"
                raise ContentNotFound()
            if os.path.exists(asset_file):
                asset_data = open(asset_file, "rb").read()

                # los fuentes del tutorial (rest) son archivos de texto plano
                # encodeados en utf-8
                if "tutorial/_sources" in asset_file:
                    return "text/plain ;charset=utf-8", asset_data

                type_ = guess_type(path)[0]
                if type_ == "text/html":
                    s = re.search("<.*?body.*?>", asset_data)
                    if s:
                        asset_data = asset_data.replace(s.group(), s.group()+WATCHDOG_IFRAME)
                return type_, asset_data
            else:
                print "WARNING: no pudimos encontrar", repr(asset_file)
                raise ContentNotFound()

        else:
            print "ERROR: path desconocido para procesar:", repr(path)

        if path=="":
            return self._main_page()

        try:
            data = self._get_contenido(path)
        except ArticleNotFound, e:
            # Devolvemos el error del artículo no encontrado usando la página
            # principal.
            _, msg = self._error_page(unicode(e))
            raise ArticleNotFound(msg)

        return data

    def institucional(self, path):
        """Sirve las páginas institucionales, wrapeadas."""
        asset_file = os.path.join(config.DIR_ASSETS, path)
        if os.path.isdir(asset_file):
            print "WARNING: ", repr(asset_file), "es un directorio"
            raise ContentNotFound()
        if not os.path.exists(asset_file):
            print "WARNING: no pudimos encontrar", repr(asset_file)
            raise ContentNotFound()

        data = open(asset_file, "rb").read()
        title = getTitleFromData(data)
        return "text/html", self._wrap(data, title)

    @ei.espera_indice
    def al_azar(self, query):
        link, tit = self.index.get_random()
        link = u"wiki" + link[5:]        
        raise Redirection(302, urllib.quote(link.encode('utf-8')))

    @ei.espera_indice
    def dosearch(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._error_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]

        # search in a thread
        buscador.buscar(self.index, keywords.decode("utf8"))
        return self._get_reloading_page(keywords)

    def ajax_index_ready(self):
        r = 'false'
        if self.index.is_ready():
            r = 'true'
        return "application/json", r

    def ajax_search(self, query):
        if not self.index.is_ready():
            raise InternalServerError("Index not ready")
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self._error_page(u"¡Búsqueda mal armada!")
        keywords = params["keywords"][0]

        # search in a thread
        buscador.buscar(self.index, keywords.decode("utf8"))
        return "text/html", "buscando?pals=%s" % (urllib.quote(keywords),)

    def ajax_search_get_results(self):
        res_completa = ""
        res_detallada = ""

        if not buscador.done_completa or not buscador.done_detallada:
            status = "NOTDONE"
        else:
            status = "DONE"
        if buscador.done_completa and buscador.results_completa:
            r = self._formatear_resultados(buscador.results_completa,
                                           buscador.buscando)
            res_completa = b64encode(r)
        if buscador.done_detallada and buscador.results_detallada:
            r = self._formatear_resultados(buscador.results_detallada,
                                           buscador.buscando)
            res_detallada = b64encode(r)

        result = '{"status":"%s","res_detallada":"%s","res_completa":"%s"}' % (
                                        status, res_detallada, res_completa)
        return "application/json", result

    def watchdog_update(self):
        self._watchdog_update()
        seconds = str(config.BROWSER_WD_SECONDS/2)
        return "text/html", "<html><head><meta http-equiv='refresh' content='%s'" \
                             "></head><body></body></html>" % (seconds, )

    def _get_reloading_page(self, palabras, res_comp=None, res_det=None):
        """Arma la página de recarga."""
        reload = RELOAD_HEADER % (serving_port,
                                  'buscando?pals=' + urllib.quote(palabras))

        aviso = "<i>(buscando%s)</i><br/>" % ("." * buscador.tardando,)
        if res_comp is None:
            res_comp = aviso
        if res_det is None:
            if res_comp == aviso:
                res_comp = ""
            res_det = aviso
        pag = self.templates("searchres", results_completa=res_comp,
                             results_detallada=res_det, header=reload,
                             buscando=palabras)
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
            results_completa = self._formatear_resultados(candidatos,
                                                          buscador.buscando)
        else:
            results_completa = ""

        # si no terminó la segunda, devolvemos hasta ahí
        if not buscador.done_detallada:
            return self._get_reloading_page(palabras, results_completa)

        # terminó la búsqueda detallada
        candidatos = buscador.results_detallada
        if candidatos:
            results_detallada = self._formatear_resultados(candidatos,
                                                           buscador.buscando)
        else:
            results_detallada = BUSQ_NO_RESULTS.encode("utf8")

        pag = self.templates("searchres", results_completa=results_completa,
                             results_detallada=results_detallada, header="",
                             buscando=palabras)
        return "text/html", self._wrap(pag, "Buscando")

    def _formatear_resultados(self, candidatos, buscando):
        """Arma los resultados."""
        # agrupamos por link, dando prioridad a los títulos de los
        # artículos originales
        agrupados = {}
        for link, titulo, ptje, original, texto in candidatos:
            # quitamos 3 dirs del link y agregamos "wiki"
            link = u"wiki" + link[5:]

            # los tokens los ponemos en minúscula porque las mayúscula les
            # da un efecto todo entrecortado
            tit_tokens = set(LIMPIA.sub("", x.lower()) for x in titulo.split())

            # si el titulo coincide exactamente con lo buscado, le damos mucho
            # puntaje para que aparezca primero...
            if titulo == buscando:
                ptje *= 10

            if link in agrupados:
                (tit, prv_ptje, tokens, txt) = agrupados[link]
                tokens.update(tit_tokens)
                if original:
                    # guardamos la info del artículo original
                    tit = titulo
                    txt = texto
                agrupados[link] = (tit, prv_ptje + ptje, tokens, txt)
            else:
                agrupados[link] = (titulo, ptje, tit_tokens, texto)

        # limpiamos los tokens
        for link, (tit, ptje, tokens, texto) in agrupados.iteritems():
            tit_tokens = set(LIMPIA.sub("", x.lower()) for x in tit.split())
            tokens.difference_update(tit_tokens)

        # ordenamos la nueva info descendiente y armamos las lineas
        res = []
        candidatos = ((k,) + tuple(v) for k,v in agrupados.iteritems())
        cand = sorted(candidatos, key=operator.itemgetter(2), reverse=True)
        for link, titulo, ptje, tokens, texto in cand:
            res.append(u'<font size=+1><a href="/%s">%s</a></font><br/>' % (
                                                                urllib.quote(link.encode("utf-8")), titulo))
            if tokens:
                res.append(u'<font color="#A05A2C"><i>%s</i></font><br/>' % (
                                                            " ".join(tokens)))
            if texto:
                res.append(u'<small>%s</small><br/>' % texto)
            res.append('<br/>')
        results = "\n".join(res)

        return results.encode("utf8")

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
        self.buscando = None

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
        self.buscando = palabras

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

def run(server_up_event, watchdog_update):
    global serving_port
    global shutdown

    WikiHTTPRequestHandler.index = cdpindex.IndexInterface(config.DIR_INDICE)
    WikiHTTPRequestHandler.index.start()
    WikiHTTPRequestHandler.protocol_version = "HTTP/1.0"
    for port in xrange(8000, 8099):
        try:
            httpd = MyHTTPServer(('', port), WikiHTTPRequestHandler)
        except socket.error, e:
            if e.args[0] != 98:  # Address already in use
                raise
        else:
            # server opened ok
            serving_port = port
            break

    print "Sirviendo HTTP en localhost, puerto %d..." % port

    shutdown = httpd.shutdown
    server_up_event.set()
    WikiHTTPRequestHandler._watchdog_update = watchdog_update
    httpd.serve_forever()

if __name__ == '__main__':
    run()
