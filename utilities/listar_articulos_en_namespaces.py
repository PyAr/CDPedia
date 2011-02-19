#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Navega las paginas que listan los articulos por Namespace para armar un listado
que luego puede ser utilizado por scraper.py para conseguir los articulos
"""

import urllib2
from functools import partial
from BeautifulSoup import BeautifulSoup
import re

UA = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.10) Gecko/20100915 Ubuntu/10.04 (lucid) Firefox/3.6.10'

WIKI = 'http://es.wikipedia.org'
TODAS = '/wiki/Especial:Todas/'
SPACES = [ u'Categoría:'.encode('utf-8'), 'Ayuda:', 'Anexo:', 'Portal:',]

req = partial(urllib2.Request, data = None, headers = {'User-Agent': UA})

def guardar_listado(soup, archivo):
    t = soup.findAll('table', {'class':'mw-allpages-table-chunk'})[0]
    titulos = [l['title'] for l in t.findAll('a')]
    archivo.write('\n'.join(titulos).encode('utf-8'))
    archivo.write('\n')

def siguiente_link(soup):
    a = soup.find('a', text=re.compile("^Siguiente p\xe1gina \("))
    if a:
        return a.findParent('a')['href']

def traer_pagina(link):
    html = urllib2.urlopen(req(link)).read()
    return BeautifulSoup(html)

if __name__ == '__main__':
    fh = open('articulos_en_namespaces.txt','w')
    for space in SPACES:
        soup = traer_pagina(WIKI + TODAS + space)
        guardar_listado(soup, fh)
        next_link = siguiente_link(soup)
        while next_link:
            print next_link
            soup = traer_pagina(WIKI + next_link)
            guardar_listado(soup, fh)
            next_link = siguiente_link(soup)

    fh.close()

