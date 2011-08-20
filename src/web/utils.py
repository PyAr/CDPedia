import re
import urllib
import os.path
import string

from src.armado import to3dirs
import config

re_header = re.compile('\<h1 id="firstHeading" class="firstHeading"\>([^\<]*)\</h1\>')
re_title = re.compile('<title>(.*)</title>')

class TemplateManager(object):
    '''Maneja los templates en disco.'''

    def __init__(self, directorio):
        self.directorio = directorio
        self.cache = {}

    def get_template(self, nombre):
        if nombre in self.cache:
            return self.cache[nombre]

        nomarch = os.path.join(self.directorio, "%s.tpl" % nombre)
        with open(nomarch, "rb") as f:
            t = string.Template(f.read())

        self.cache[nombre] = t
        return t

def get_title_from_data(data):
    if data is None:
        return ""
    for regexp in (re_header, re_title):
        match = regexp.search(data)
        if match is not None:
            return match.group(1)
    return ""


def get_orig_link(path):
    """A partir del path devuelve el link original externo."""
    orig_link = config.URL_WIKIPEDIA + u"wiki/" + \
                to3dirs.to_pagina(path)
    return orig_link
