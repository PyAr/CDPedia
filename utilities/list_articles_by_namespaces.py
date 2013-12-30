#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Generate the article listing per Namespace.

Navigate the pages that list articles per Namespace to build a list that can
be used later by scraper.py to get the article pages.
"""

import re
import urllib
import urllib2

from functools import partial

from BeautifulSoup import BeautifulSoup

UA = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.10) '\
     'Gecko/20100915 Ubuntu/10.04 (lucid) Firefox/3.6.10'
WIKI = 'http://es.wikipedia.org'
TODAS = '/wiki/Especial:Todas/'
SPACES = [u'Categoría:'.encode('utf-8'), 'Ayuda:', 'Anexo:', 'Portal:']

req = partial(urllib2.Request, data=None, headers={'User-Agent': UA})

def guardar_listado(soup, archivo):
    t = soup.findAll('table', {'class':'mw-allpages-table-chunk'})[0]
    links = [l['href'].replace('/wiki/','') for l in t.findAll('a')]
    links = [urllib.unquote(l.encode("utf8")) for l in links]
    archivo.write('\n'.join(links))
    archivo.write('\n')

def siguiente_link(soup):
    a = soup.find('a', text=re.compile("^Siguiente p\xe1gina \("))
    if a:
        return a.findParent('a')['href']

def traer_pagina(link):
    html = urllib2.urlopen(req(link)).read()
    return BeautifulSoup(html)

def main():
    fh = open('articles_by_namespaces.txt', 'wb')
    for space in SPACES:
        soup = traer_pagina(WIKI + TODAS + space)
        guardar_listado(soup, fh)
        next_link = siguiente_link(soup)
        while next_link:
            soup = traer_pagina(WIKI + next_link)
            guardar_listado(soup, fh)
            next_link = siguiente_link(soup)

    fh.close()

if __name__ == '__main__':
    main()
