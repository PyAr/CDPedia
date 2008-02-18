#!/usr/bin/python2.4
# cdpedia/server.py
"""server"""

from __future__ import division

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


__version__ = "0.1.1.1.1.1"

indexfilename = "indexes/wikiindex"

reg = re.compile("\<title\>([^\<]*)\</title\>")
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
    #index = cdpindex.Index(indexfilename)
        
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
            self.end_headers ()
            self.wfile.write ("URL not found: %s" % self.path)
        
    def getfile(self, path):
        scheme, netloc, path, params, query, fragment = urllib2.urlparse.urlparse(path)
        path = urllib.unquote(path)
        print path
        if path == "/search":
            return self.search()
        if path == "/dosearch":
            return self.dosearch(query)
        if path[0] == "/":
            path = path[1:]
        print path

        if path.split("/")[0] in ("images","raw","skins"):
            return "image/%s"%path[-3:], open("salida/assets/"+path).read()
        if path=="":
            return self.search()
        path =  self.root + path
        print path
        
        match = re.match(".\/.\/.\/(.*)", path)
        if match is not None:
            path = match.group(1)
        print path

        try:
            if path[-4:]=="html": 
                print "!!!!", path
                data = decompresor.getArticle(path)
            else:
                # TODO: fire up the search "didn't you really mean <this>?"
                return (None, None)
        except:
            print "ERROR: not found:", path
            data = wikipedia.read(self.root + "index.html")
            
        return "text/html",data

    def search(self):
        return "text/html", """
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es" lang="es" dir="ltr"> <head> <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" /> 
</head><body>
        <form method="get" action="/dosearch">
        <input name="keywords"></input>
        <input type="submit">
        </form></body></html>"""
        
    def dosearch(self, query):
        params = cgi.parse_qs(query)
        if not "keywords" in params:
            return self.search()
        keywords = params["keywords"][0]
        candidatos = index.search( keywords )
        res = []
        for c,t in candidatos:
            #link =  urllib.quote(unicode(c[len(self.root):], 'utf-8')).encode('ascii')
            link=c[len(self.root):]
            print link
            res.append('<tr><td><a href="%s">%s</a></td></tr>'%(link,t))
        
        return "text/html", """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es" lang="es" dir="ltr"> <head> <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" /> 
</head><body>
        <table>
        %s
        </table>
        </body></html>"""%( "\n".join( res ) )
        
    
def run(HandlerClass = WikiHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer,
         build_index=False, maxitems=50):
    #WikiHTTPRequestHandler.index = index
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
	#index = cdpindex.Index(indexfilename)
	run()
