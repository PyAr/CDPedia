# -*- coding: utf-8 -*-

import os
import re
import urllib
import urlparse
import posixpath
from mimetypes import guess_type

import utils
import bmp
import config
from src.armado import compresor
from src.armado import cdpindex
from src.armado import to3dirs
from destacados import Destacados
from utils import TemplateManager
from src import third_party # Need this to import thirdparty (werkzeug and jinja2)
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader


class ArticleNotFound(HTTPException):
    code = 404

    def __init__(self, article_name, original_link, description=None):
        HTTPException.__init__(self, description)
        self.article_name = article_name
        self.original_link = original_link


class CDPedia(object):

    def __init__(self, watchdog):
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                 autoescape=False)

        self.jinja_env.globals["watchdog"] = True if watchdog else False

        self.template_manager = TemplateManager(template_path)
        self._art_mngr = compresor.ArticleManager()
        self._img_mngr = compresor.ImageManager()
        self._destacados_mngr = Destacados(self._art_mngr, debug=False)

        self.index = cdpindex.IndexInterface(config.DIR_INDICE)
        self.index.start()

        self.watchdog = watchdog

        self.url_map = Map([
            Rule('/', endpoint='main_page'),
            Rule('/wiki/<nombre>', endpoint='articulo'),
            Rule('/al_azar', endpoint='al_azar'),
            Rule('/images/<path:nombre>', endpoint='imagen'),
            Rule('/institucional/<path:path>', endpoint='institucional'),
            Rule('/watchdog/update', endpoint='watchdog_update'),
        ])

    def on_main_page(self, request):
        data_destacado = self._destacados_mngr.get_destacado()
        destacado = None
        if data_destacado is not None:
            link, title, first_paragraphs = data_destacado
            destacado = {"link":link, "title":title,
                         "first_paragraphs":first_paragraphs}
        return self.render_template('main_page.html',
            title="Portada",
            destacado=destacado,
        )

    def on_articulo(self, request, nombre):
        orig_link = utils.get_orig_link(nombre)
        try:
            data = self._art_mngr.get_item(nombre)
        except Exception, e:
            raise InternalServerError(u"Error interno al buscar contenido: %s" % e)

        if data is None:
            raise ArticleNotFound(nombre, orig_link)

        title = utils.get_title_from_data(data)
        return self.render_template('article.html',
            article_name=nombre,
            orig_link=orig_link,
            article=data
        )

    def on_imagen(self, request, nombre):
        try:
            normpath = posixpath.normpath(nombre)
            asset_data = self._img_mngr.get_item(normpath)
        except Exception, e:
            msg = u"Error interno al buscar imagen: %s" % e
            raise InternalServerError(msg)
        if asset_data is None:
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

        data = open(asset_file, "rb").read()
        title = utils.get_title_from_data(data)

        return self.render_template('institucional.html',
            title=title,
            asset=data.decode("utf-8")
        )

    #@ei.espera_indice # TODO
    def on_al_azar(self, request):
        link, tit = self.index.get_random()
        link = u"wiki/" + to3dirs.from_path(link)
        return redirect(urllib.quote(link.encode("utf-8")))

    def on_watchdog_update(self, request):
        self.watchdog.update()
        seconds = str(int(config.BROWSER_WD_SECONDS * 0.85))
        resp = Response("<html><head><meta http-equiv='refresh' content='%s'" \
                        "></head><body></body></html>" % seconds,
                        mimetype="text/html")
        return resp

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except ArticleNotFound, e:
            response =  self.render_template("404.html",
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


def create_app(watchdog, with_static=True, with_debugger=True, use_evalex=True):
    from werkzeug.wsgi import SharedDataMiddleware
    from werkzeug.debug import DebuggedApplication
    app = CDPedia(watchdog)
    if with_static:
        paths = [("/" + path, os.path.join(config.DIR_ASSETS, path))
                 for path in config.ALL_ASSETS]
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, dict(paths))
    if with_debugger:
        app.wsgi_app = DebuggedApplication(app.wsgi_app, use_evalex)
    return app

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 8000, app, use_debugger=True, use_reloader=False,
               threaded=True)
