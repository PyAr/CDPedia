"""lanzador para windows"""
import imp

# imports explicitos cdpedia no en third party, para que cxfreeze
# encuentre los modulos stdlib usados
import os
import sys
import codecs
import platform
import optparse
import threading
import traceback
import webbrowser

# Importamos los modulos / packages en third_party para que cxfreeze pueda
# incluir las partes de stdlib que usen esos modulos
# Notar que tenemos un .pth en site-packages apuntando a ese directorio
#import werkzeug
import jinja2

# imports stdlib que se le escaparon a cxfreeze y ponemos explicitos 
import SocketServer
##import urllib
##import BaseHTTPServer
##import Cookie
##import htmlentitydefs
##import urllib2
import Queue
import uuid
#import MarkupSafe

if hasattr(sys, "frozen"):
    win32main_path = unicode(sys.executable, sys.getfilesystemencoding( ))
else:
    win32main_path = os.path.abspath(__file__)
print 'win32main_path:', win32main_path.__repr__()

cdpedia_path = os.path.normpath(win32main_path + '\\..\\..\\..\\..' )
print 'lanzador, cdpedia_path:', cdpedia_path

#sys.path.insert(0, cdpedia_path)
os.chdir(cdpedia_path)

imp.load_source("__main__", "cdpedia.py")
