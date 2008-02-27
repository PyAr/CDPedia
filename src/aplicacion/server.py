#!/usr/bin/python2.4
# cdpedia/server.py
"""server"""

from __future__ import division

import BaseHTTPServer
import cgi
import mimetypes
import os
import pickle
import posixpath
import shutil
import urllib   # .quote, .unquote
import urllib2  # .urlparse
import zipfile
from StringIO import StringIO


import cPickle, re
import cdpindex


__version__ = "0.1.1.1.1.1"

zipfilename = "es.zip"
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
    
    #wikipedia = zipfile.ZipFile(zipfilename)
    root = ""
    #index = cdpindex.Index(indexfilename)
        
    def do_GET(self):
        """Serve a GET request."""
        tipo, data = self.getfile(self.path)
        self.send_response(200)
        #self.send_header("Content-type", tipo)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)
        
    def getfile(self, path):
        scheme, netloc, path, params, query, fragment = urllib2.urlparse.urlparse(path)
        path = urllib.unquote(path)
        if path == "/search":
            return self.search()
        if path == "/dosearch":
            return self.dosearch(query)
        if path[0] == "/":
            path = path[1:]
        if path=="":
            return self.search()
            path = "index.html"
        path =  self.root + path
        try:
            if path[-4:]=="html": print "!!!!", path
            data = wikipedia.read(path)
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
        
import time
class Timer:
    def start(self, total):
        self.start_time = self.last_tick = time.time()
        self.total = total
        self.done = 0
        
    def tick(self, amount=1):
        now = time.time()
        self.done += amount
        speed = (amount/(now - self.last_tick ))
        print self.done, "/", self.total , "(%0.2f%%)"%(float(self.done)/float(self.total)*100)
        print "\t Elapsed:", self.show( now - self.start_time )
        print "\t Actual Speed:", "%0.7f items per second"%speed
        print "\t ETA:", self.show( (self.total-self.done)/speed)
        self.last_tick = now
        
    def show(self, seconds):
        hours = seconds / (60*60)
        minutes = (seconds%(60*60) ) / 60
        seconds_left = seconds % 60
        return "%02i:%02i:%02i"%(hours, minutes, seconds_left)
    
def build_index(maxitems=0):
    parsed_file = "parsed/parsefile.cpkl"

    print "Opening Index:", indexfilename
    index = cdpindex.Index(indexfilename) 
    print "Opening contents:", zipfilename
    wikipedia = zipfile.ZipFile(zipfilename)
    print "Stage 1:"
    try:
        f = open(parsed_file)
        print "Loading parsed pages"
        all = cPickle.load(f)
    except IOError:
        print "Creating parsed pages"
        timer = Timer()
        print "Generating namelist"
        namelist = list(wikipedia.namelist())
        total = len(namelist)
        print "Done with namelist"
        timer.start(len(namelist))
        all = []
        for i,name in enumerate(namelist):
            if maxitems and i>maxitems: break
            if i%50==0:
                timer.tick(50)
                
            if name.endswith(".html"):
                title = gettitle(wikipedia, name)
                all.append( (name, title) )
        cPickle.dump( all, open(parsed_file, "w") )
    print "Done." 
            
    timer = Timer()
    timer.start(len(all))
    for i,(name, title) in enumerate(all):
        if maxitems and i>maxitems: break
        if i%50==0:
            timer.tick(50)
        if name.endswith(".html"):
            index.index(name, title)
        if i%50==0:
            index.flush()
    index.save()
    print "Exiting..."
    
def run(HandlerClass = WikiHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer,
         build_index=False, maxitems=50):
    WikiHTTPRequestHandler.index = index
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    if 0:
        import BeautifulSoup, re
        build_index()
    else:
        wikipedia = zipfile.ZipFile(zipfilename)
        index = cdpindex.Index(indexfilename)
        run()
