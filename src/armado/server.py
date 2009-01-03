#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
# cdpedia/server.py
"""server"""

from __future__ import division

class ContentNotFound(Exception):
    """No se encontró la página requerida!"""

header = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es" lang="es" dir="ltr">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
            <meta name="keywords" content="Universidad,1088,1492,1918,258,387 adC,489,529,637,651,976" />
        <link rel="shortcut icon" href="/favicon.ico" />
        <link rel="search" type="application/opensearchdescription+xml" href="/w/opensearch_desc.php" title="Wikipedia (Español)" />
        <link rel="copyright" href="../../../COPYING.html" />
    <title>[TITLE_GOES_HERE] - Wikipedia, la enciclopedia libre</title>
    <style type="text/css">/*<![CDATA[*/ @import "../../../skins/htmldump/main.css"; /*]]>*/</style>
    <link rel="stylesheet" type="text/css" media="print" href="../../../skins/common/commonPrint.css" />
    <!--[if lt IE 5.5000]><style type="text/css">@import "../../../skins/monobook/IE50Fixes.css";</style><![endif]-->
    <!--[if IE 5.5000]><style type="text/css">@import "../../../skins/monobook/IE55Fixes.css";</style><![endif]-->
    <!--[if IE 6]><style type="text/css">@import "../../../skins/monobook/IE60Fixes.css";</style><![endif]-->
    <!--[if IE]><script type="text/javascript" src="../../../skins/common/IEFixes.js"></script>
    <meta http-equiv="imagetoolbar" content="no" /><![endif]-->
    <script type="text/javascript" src="../../../skins/common/wikibits.js"></script>
    <script type="text/javascript" src="../../../skins/htmldump/md5.js"></script>
    <script type="text/javascript" src="../../../skins/htmldump/utf8.js"></script>
    <script type="text/javascript" src="../../../skins/htmldump/lookup.js"></script>
    <script type="text/javascript" src="../../../raw/gen.js"></script>        <style type="text/css">/*<![CDATA[*/
@import "../../../raw/MediaWiki%7ECommon.css";
@import "../../../raw/MediaWiki%7EMonobook.css";
@import "../../../raw/gen.css";
/*]]>*/</style>          </head>
  <body
    class="ns-0">
    <div id="globalWrapper">
      <div id="column-content">
    <div id="content">
      <a name="top" id="contentTop"></a>
      <div id="bodyContent">
"""

footer = """
        <div class="visualClear"></div>
      </div>
    </div>
      </div>
      <div id="column-one">
    <div id="p-cactions" class="portlet">
      <h5>Views</h5>
      <ul>
        <li id="ca-nstab-main"
           class="selected"        ><a href="../../../u/n/i/Universidad.html">Artículo</a></li><li id="ca-talk"
                   ><a href="../../../u/n/i/Discusi%C3%B3n%7EUniversidad_a48b.html">Discusión</a></li><li id="ca-current"
                   ><a href="http://es.wikipedia.org/wiki/Universidad">Revisión actual</a></li>   </ul>
    </div>
    <div class="portlet" id="p-logo">
      <a style="background-image: url(http://upload.wikimedia.org/wikipedia/commons/7/74/Wikipedia-logo-es.png);"
        href="../../../index.html"
        title="Portada"></a>
    </div>
    <script type="text/javascript"> if (window.isMSIE55) fixalpha(); </script>
        <div class='portlet' id='p-navigation'>
      <h5>Navegación</h5>
      <div class='pBody'>
        <ul>
                  <li id="n-mainpage"><a href="../../../index.html">Portada</a></li>
                  <li id="n-portal"><a href="../../../c/o/m/Portal%7EComunidad_753e.html">Portal de la comunidad</a></li>
                  <li id="n-currentevents"><a href="../../../a/c/t/Portal%7EActualidad_c11d.html">Actualidad</a></li>
                  <li id="n-help"><a href="../../../c/o/n/Ayuda%7EContenidos_3c64.html">Ayuda</a></li>
                  <li id="n-sitesupport"><a href="http://wikimediafoundation.org/wiki/Donaciones">Donativos</a></li>
                </ul>
      </div>
    </div>
        <div id="p-search" class="portlet">
      <h5><label for="searchInput">Buscar</label></h5>
      <div id="searchBody" class="pBody">
        <form action="javascript:goToStatic(3)" id="searchform"><div>
          <input id="searchInput" name="search" type="text"
            accesskey="f" value="" />
          <input type='submit' name="go" class="searchButton" id="searchGoButton"
            value="Ir" />
        </div></form>
      </div>
    </div>
          </div><!-- end of the left (by default at least) column -->
      <div class="visualClear"></div>
      <div id="footer">
    <div id="f-poweredbyico"><a href="http://www.mediawiki.org/"><img src="../../../skins/common/images/poweredby_mediawiki_88x31.png" alt="Powered by MediaWiki" /></a></div>  <div id="f-copyrightico"><a href="http://wikimediafoundation.org/"><img src="../../../images/wikimedia-button.png" border="0" alt="Wikimedia Foundation"/></a></div>    <ul id="f-list">
                 <li id="f-copyright">Contenido disponible bajo los términos de la <a class="internal" href="/wiki/Wikipedia:Texto_de_la_Licencia_de_documentación_libre_de_GNU">Licencia de documentación libre de GNU</a> (véase <b><a class="internal" href="/wiki/Wikipedia:Derechos_de_autor">Derechos de autor</a></b>).<br />
Wikipedia® es una marca registrada de la organización sin ánimo de lucro <a class="internal" href="http://wikimediafoundation.org/wiki/Portada">Wikimedia Foundation, Inc.</a><br /></li>     <li id="f-about"><a href="../../../a/c/e/Wikipedia%7EAcerca_de_959f.html" title="Wikipedia:Acerca de">Acerca de Wikipedia</a></li>      <li id="f-disclaimer"><a href="../../../l/i/m/Wikipedia%7ELimitaci%C3%B3n_general_de_responsabilidad_a0a2.html" title="Wikipedia:Limitación general de responsabilidad">Aviso legal</a></li>      </ul>
      </div>
    </div>
  </body>
</html>
"""

mainpage_header = """
<html><head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<title>CDPedia - PyAr</title>
</head><body><br>
<center>
<font color="#0000ff" size="+3">CD Pedia<br>
<br>

<font color="#ff0000" size="+2">
"""

mainpage_footer = """
<br>

<br>
<font color="#000000" size="+2">Buscar en los títulos<br><br>

<table>
<tr>
 <td valign="top">Palabras completas</td>
 <td>
    <form method="get" action="/dosearch">
    <input name="keywords"></input>
    <input type="submit" value="Buscar">
    </form>
 </td>
</tr>
<tr>
 <td valign="top">Búsqueda detallada</td>
 <td>
    <form method="get" action="/detallada">
    <input name="keywords"></input>
    <input type="submit" value="Buscar">
    </form>
 </td>
</tr>
</table>

<br>
<font color="#000000" size="+2">Ver páginas<br><br>
<table>
<tr>
 <td>
    <form method="get" action="/listfull">
    <input type="submit" value="Listado completo"></input>
    </form>
 </td>
 <td>
    <form method="get" action="/al_azar">
    <input type="submit" value="Alguna al azar"></input>
    </form>
 </td>
</tr>
</table>

<font size="-1">
<br>
- - - <br>
Otro desarrollo de PyAr - Python Argentina
</font>
</center>
 </body></html>
"""


import BaseHTTPServer
import cgi
import mimetypes
import os
import posixpath
import shutil
import urllib   # .quote, .unquote
import urllib2  # .urlparse
import zipfile
from StringIO import StringIO


import cPickle, re
import cdpindex
import decompresor
import config


__version__ = "0.1.1.1.1.1"

reg = re.compile("\<title\>([^\<]*)\</title\>")
reHeader1 = re.compile('\<h1 class="firstHeading"\>([^\<]*)\</h1\>')

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

    root = ""

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
#        print "======== contenido", path
        match = re.match("[^/]+\/[^/]+\/[^/]+\/(.*)", path)
        if match is not None:
            path = match.group(1)

        if path[-4:] != "html":
            raise ContentNotFound(u"Sólo buscamos páginas HTML!")

        try:
            data = decompresor.getArticle(path.decode("utf-8"))
        except Exception, e:
            msg = u"Error interno al buscar contenido: %s" % e
            raise ContentNotFound(msg)

        if data is None:
            raise ContentNotFound(u"No se encontró la página '%s'" % path)

        title = getTitleFromData(data)

        pag = header.replace("[TITLE_GOES_HERE]",title) + data + footer
        return pag

    def _main_page(self, msg=u"¡Bienvenido!"):
        pag = mainpage_header + msg.encode("utf8") + mainpage_footer
        return "text/html", pag

    def getfile(self, path):
        scheme, netloc, path, params, query, fragment = urllib2.urlparse.urlparse(path)
        path = urllib.unquote(path)
        print "get file:", path
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

        if path.split("/")[0] in ("images","raw","skins"):
            asset_file = os.path.join(config.DIR_ASSETS, path)
            asset_data = open(asset_file).read()
            return "image/%s"%path[-3:], asset_data
        if path=="":
            return self._main_page()
        path =  self.root + path

        try:
            data = self._get_contenido(path)
        except ContentNotFound, e:
            msg = u"ERROR: '%s' not found (%s)" % (path, e.message)
            return self._main_page(msg)

        return "text/html",data

    def detallada(self, query):
        return self._main_page(u"Todavía no codeamos esa funcionalidad, :s")

    def listfull(self, query):
        return self._main_page(u"Todavía no codeamos esa funcionalidad, :s")

    def al_azar(self, query):
        return self._main_page(u"Todavía no codeamos esa funcionalidad, :s")

    def dosearch(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self.search()
        keywords = params["keywords"][0]
        candidatos = self.index.search( keywords )
        if not candidatos:
            return self._main_page(u"No se encontró nada para lo ingresado!")
        res = []
        for camino, titulo in candidatos:
            #link =  urllib.quote(unicode(c[len(self.root):], 'utf-8')).encode('ascii')
            link = camino[len(self.root):]
            res.append('<tr><td><a href="%s">%s</a></td></tr>' % (link, titulo))

        return "text/html", """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es" lang="es" dir="ltr"> <head> <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body>
        <table>
        %s
        </table>
        </body></html>"""%( "\n".join( res ) )


def run(HandlerClass = WikiHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer,
         build_index=False, maxitems=50):
    WikiHTTPRequestHandler.index = cdpindex.Index(config.PREFIJO_INDICE)
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    run()
