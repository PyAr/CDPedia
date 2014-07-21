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


import codecs
import gettext
import operator
import os
import posixpath
import re
import tarfile
import tempfile
import urllib

from mimetypes import guess_type

import utils
import bmp
import config

from src.armado import compresor
from src.armado import cdpindex
from src.armado.cdpindex import normaliza as normalize_keyword
from src.armado import to3dirs
from destacados import Destacados
from searcher import Searcher
from utils import TemplateManager
from src import third_party  # Need this to import 3rd_party (werkzeug, jinja2)
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader

ARTICLES_BASE_URL = u"wiki"


class ArticleNotFound(HTTPException):
    code = 404

    def __init__(self, article_name, original_link, description=None):
        HTTPException.__init__(self, description)
        self.article_name = article_name
        self.original_link = original_link


class CDPedia(object):

    def __init__(self, watchdog=None, verbose=False, search_cache_size=100):
        self.search_cache_size = search_cache_size
        self.watchdog = watchdog
        self.verbose = verbose

        self.art_mngr = compresor.ArticleManager(verbose=verbose)

        # Configure template engine (jinja)
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     extensions=['jinja2.ext.i18n'],
                                     autoescape=False)
        self.jinja_env.globals["watchdog"] = True if watchdog else False
        translations = gettext.translation("core", 'locale',
                                           [self.art_mngr.language])
        self.jinja_env.install_gettext_translations(translations)

        self.template_manager = TemplateManager(template_path)
        self.img_mngr = compresor.ImageManager(verbose=verbose)
        self.destacados_mngr = Destacados(self.art_mngr, debug=False)

        self.index = cdpindex.IndexInterface(config.DIR_INDICE)
        self.index.start()

        self.searcher = Searcher(self.index, self.search_cache_size)
        self.tmpdir = os.path.join(tempfile.gettempdir(), "cdpedia")

        self.url_map = Map([
            Rule('/', endpoint='main_page'),
            Rule('/%s/<nombre>' % ARTICLES_BASE_URL, endpoint='articulo'),
            Rule('/al_azar', endpoint='al_azar'),
            Rule('/search', endpoint='search'),
            Rule('/search/<key>', endpoint='search_results'),
            Rule('/images/<path:nombre>', endpoint='imagen'),
            Rule('/institucional/<path:path>', endpoint='institucional'),
            Rule('/watchdog/update', endpoint='watchdog_update'),
            Rule('/search_index/ready', endpoint='index_ready'),
            Rule('/tutorial', endpoint='tutorial'),
        ])
        self._tutorial_ready = False

    def on_main_page(self, request):
        data_destacado = self.destacados_mngr.get_destacado()
        destacado = None
        if data_destacado is not None:
            link, title, first_paragraphs = data_destacado
            destacado = {"link": link, "title": title,
                         "first_paragraphs": first_paragraphs}

        # this is a hack while we have statically the portals for 'es'; will
        # change in a future where all portals are dinamically built with the
        # rest of the CDPedia
        if self.art_mngr.language == 'es':
            _path = os.path.join(config.DIR_ASSETS, 'static', 'portales.html')
            with codecs.open(_path, "rb", encoding='utf8') as fh:
                portales = fh.read()
        else:
            portales = ""

        return self.render_template('main_page.html',
            title="Portada",
            destacado=destacado,
            portales=portales,
        )

    def on_articulo(self, request, nombre):
        orig_link = utils.get_orig_link(nombre)
        try:
            data = self.art_mngr.get_item(nombre)
        except Exception, e:
            raise InternalServerError(u"Error interno al buscar contenido: %s" % e)

        if data is None:
            raise ArticleNotFound(nombre, orig_link)

        return self.render_template('article.html',
            article_name=nombre,
            orig_link=orig_link,
            article=data,
            language=self.art_mngr.language,
        )

    def on_imagen(self, request, nombre):
        try:
            normpath = posixpath.normpath(nombre)
            asset_data = self.img_mngr.get_item(normpath)
        except Exception, e:
            msg = u"Error interno al buscar imagen: %s" % e
            raise InternalServerError(msg)
        if asset_data is None:
            if self.verbose:
                print "WARNING: no pudimos encontrar", repr(nombre)
            try:
                width, _, height = request.args["s"].partition('-')
                width = int(width)
                height = int(height)
            except Exception, e:
                raise InternalServerError("Error al generar imagen")
            img = bmp.BogusBitMap(width, height)
            return Response(img.data, mimetype="img/bmp")
        type_ = guess_type(nombre)[0]
        return Response(asset_data, mimetype=type_)

    def on_institucional(self, request, path):
        path = os.path.join("institucional", path)
        asset_file = os.path.join(config.DIR_ASSETS, path)
        if os.path.isdir(asset_file):
            print "WARNING: ", repr(asset_file), "es un directorio"
            raise NotFound()
        if not os.path.exists(asset_file):
            print "WARNING: no pudimos encontrar", repr(asset_file)
            raise NotFound()

        # all unicode
        data = codecs.open(asset_file, "rb", "utf8").read()
        title = utils.get_title_from_data(data)

        p = self.render_template('institucional.html', title=title, asset=data)
        return p

    #@ei.espera_indice # TODO
    def on_al_azar(self, request):
        link, tit = self.index.get_random()
        link = "%s/%s" % (ARTICLES_BASE_URL, to3dirs.from_path(link))
        return redirect(urllib.quote(link.encode("utf-8")))

    #@ei.espera_indice # TODO
    def on_search(self, request):
        if request.method == "GET":
            return self.render_template('search.html')
        elif request.method == "POST":
            search_string = request.form.get("keywords", None)
            search_string = urllib.unquote_plus(search_string)
            if search_string:
                search_string_norm = normalize_keyword(search_string)
                words = search_string_norm.split()
                self.searcher.start_search(words)
                return redirect("/search/%s" % "+".join(words))
            return redirect("/")

    def on_search_results(self, request, key):
        search_string_norm = urllib.unquote_plus(normalize_keyword(key))
        words = search_string_norm.split()
        start = int(request.args.get("start", 0))
        quantity = int(request.args.get("quantity", config.SEARCH_RESULTS))
        id_ = self.searcher.start_search(words)
        results = self.searcher.get_results(id_, start, quantity)

        CLEAN = re.compile("[(),]")

        # group by link, giving priority to the title of the original articles
        grouped_results = {}
        for link, title, ptje, original, texto in results:
            # remove 3 dirs from link and add the proper base url
            link = "%s/%s" % (ARTICLES_BASE_URL, to3dirs.from_path(link))

            # convert tokens to lower case
            tit_tokens = set(CLEAN.sub("", x.lower()) for x in title.split())

            if link in grouped_results:
                (tit, prv_ptje, tokens, txt) = grouped_results[link]
                tokens.update(tit_tokens)
                if original:
                    # save the info of the original article
                    tit = title
                    txt = texto
                grouped_results[link] = (tit, prv_ptje + ptje, tokens, txt)
            else:
                grouped_results[link] = (title, ptje, tit_tokens, texto)

        # clean the tokens
        for link, (tit, ptje, tokens, texto) in grouped_results.iteritems():
            tit_tokens = set(CLEAN.sub("", x.lower()) for x in tit.split())
            tokens.difference_update(tit_tokens)

        # sort the results
        candidates = ((k, ) + tuple(v) for k, v in grouped_results.iteritems())
        sorted_results = sorted(candidates, key=operator.itemgetter(2),
                                reverse=True)

        return self.render_template('search.html',
            search_words=words,
            results=sorted_results,
            start=start,
            quantity=quantity
        )

    def on_tutorial(self, request):
        tmpdir = os.path.join(self.tmpdir)
        if not self._tutorial_ready:
            if not os.path.exists(tmpdir):
                tar = tarfile.open(os.path.join(config.DIR_ASSETS,
                                   "tutorial.tar.bz2"), mode="r:bz2")
                tar.extractall(tmpdir)
                tar.close()
            self._tutorial_ready = True
        asset = "/cmp/tutorial/index.html"
        return self.render_template('compressed_asset.html',
                                    server_mode=config.SERVER_MODE,
                                    asset_url=asset,
                                    asset_name=u"Tutorial de python")

    def on_watchdog_update(self, request):
        self.watchdog.update()
        seconds = str(int(config.BROWSER_WD_SECONDS * 0.85))
        resp = Response("<html><head><meta http-equiv='refresh' content='%s'" \
                        "></head><body></body></html>" % seconds,
                        mimetype="text/html")
        return resp

    def on_index_ready(self, request):
        r = 'false'
        if self.index.is_ready():
            r = 'true'
        return Response(r, mimetype="application/json")

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except ArticleNotFound, e:
            response = self.render_template("404.html",
                                            article_name=e.article_name,
                                            original_link=e.original_link)
            response.status_code = 404
            return response
        except InternalServerError, e:
            response = self.render_template("500.html", message=e.description)
            response.status_code = 500
            return response
        except HTTPException, e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app(watchdog, verbose=False, with_static=True, with_debugger=True,
               use_evalex=True):
    from werkzeug.wsgi import SharedDataMiddleware
    from werkzeug.debug import DebuggedApplication
    app = CDPedia(watchdog, verbose=verbose)
    if with_static:
        paths = [("/" + path, os.path.join(config.DIR_ASSETS, path))
                 for path in config.ALL_ASSETS]
        paths += [('/cmp', app.tmpdir)]
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, dict(paths))
    if with_debugger:
        app.wsgi_app = DebuggedApplication(app.wsgi_app, use_evalex)
    return app

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 8000, app, use_debugger=True, use_reloader=False,
               threaded=True)
