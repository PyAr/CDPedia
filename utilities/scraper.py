#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2010-2012 CDPedistas (see AUTHORS.txt)
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

"""Download the whole wikipedia."""

from __future__ import with_statement

import StringIO
import collections
import datetime
import functools
import gzip
import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib

from twisted.internet import defer, reactor
from twisted.web import client, error, http

import workerpool

# import stuff from project's trunk
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.armado import to3dirs

# log all bad stuff
_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("scraper.log")
_logger.addHandler(handler)
_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s  %(message)s")
handler.setFormatter(formatter)
logger = functools.partial(_logger.log, logging.INFO)

WIKI = 'http://%(lang)s.wikipedia.org/'

HISTORY_BASE = (
    'http://%(lang)s.wikipedia.org/w/api.php?action=query&prop=revisions'
    '&format=json&rvprop=ids|timestamp|user|userid'
    '&rvlimit=%(limit)d&titles=%(title)s'
)
REVISION_URL = (
    'http://%(lang)s.wikipedia.org/w/index.php?'
    'title=%(title)s&oldid=%(revno)s'
)

USER_AGENT = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.10) '\
             'Gecko/20100915 Ubuntu/10.04 (lucid) Firefox/3.6.10'

REQUEST_HEADERS = {'Accept-encoding':'gzip'}

DataURLs = collections.namedtuple("DataURLs",
                                  "url temp_dir disk_name, basename")

class URLAlizer(object):
    def __init__(self, listado_nombres, dest_dir, language):
        self.language = language
        self.dest_dir = dest_dir
        self.temp_dir = dest_dir + ".tmp"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.fh = open(listado_nombres, 'r')

    def next(self):
        while True:
            line = self.fh.readline().strip()
            if line == "":
                raise StopIteration
            if line == "page_title":
                continue
            basename = line.decode("utf-8").strip()
            path = os.path.join(self.dest_dir, to3dirs.to_path(basename))
            disk_name = os.path.join(path, to3dirs.to_filename(basename))
            if not os.path.exists(disk_name.encode('utf-8')):
                if not os.path.exists(path.encode('utf-8')):
                    os.makedirs(path.encode('utf-8'))

                quoted_url = urllib.quote(basename.encode('utf-8'))
                # Skip wikipedia automatic redirect
                wiki = WIKI % dict(lang=self.language)
                url = wiki + "w/index.php?title=%s&redirect=no" % (quoted_url,)
                data = DataURLs(url=url, temp_dir=self.temp_dir,
                                disk_name=disk_name, basename=basename)
                return data

    def __iter__(self):
        return self


@defer.inlineCallbacks
def fetch_html(url):
    """Fetch an url following redirects."""
    retries = 3
    while True:
        try:
            data = yield client.getPage(url, headers=REQUEST_HEADERS,
                                        timeout=60, agent=USER_AGENT)
            compressedstream = StringIO.StringIO(data)
            gzipper = gzip.GzipFile(fileobj=compressedstream)
            html = gzipper.read()

            defer.returnValue(html)
        except Exception, err:
            if isinstance(err, error.Error) and err.status == http.NOT_FOUND:
                raise
            retries -= 1
            if not retries:
                raise


class PageHaveNoRevisions(Exception):
    pass


class WikipediaArticleHistoryItem(object):
    def __init__(self, user_registered, page_rev_id, date):
        self.user_registered = user_registered
        self.page_rev_id = page_rev_id
        self.date = date

    @classmethod
    def FromJSON(cls, jsonitem):
        user_registered = jsonitem.get('userid', 0) != 0
        page_rev_id = str(jsonitem['revid'])
        tstamp = jsonitem['timestamp']
        date = datetime.datetime.strptime(tstamp, "%Y-%m-%dT%H:%M:%SZ")
        return cls(user_registered, page_rev_id, date)

    def __str__(self):
        return '<rev: regist %s id %r %r>' % (self.user_registered,
                                              self.page_rev_id, self.date)


class WikipediaArticle(object):
    """Represent a wikipedia page.

    It should know how to retrive the asociated history page and any revision.
    """
    HISTORY_CLASS =  WikipediaArticleHistoryItem

    def __init__(self, language, url, basename):
        self.language = language
        self.url = url
        self.basename = basename
        self.quoted_basename = urllib.quote(
            basename.encode('utf-8')).replace(' ', '_')
        self._history = None
        self.history_size = 6

    def __str__(self):
        return '<wp: %s>' % (self.basename.encode('utf-8'),)

    @property
    def history_url(self):
        url = HISTORY_BASE % dict(lang=self.language, limit=self.history_size,
                                  title=self.quoted_basename)
        return url

    def get_revision_url(self, revision=None):
        """
        Return the revision url when revision is provided, elsewhere the basic
        url for the page
        """
        if revision is None:
            return self.url
        url = REVISION_URL % dict(
            lang=self.language, title=self.quoted_basename, revno=revision)
        return url

    @defer.inlineCallbacks
    def get_history(self, size=6):
        if self._history is None or size!=self.history_size:
            self.history_size = size
            self._history = yield fetch_html(self.history_url)
        defer.returnValue(self._history)

    def iter_history_json(self, json_rev_history):
        pages = json_rev_history['query']['pages']
        assert len(pages) == 1
        pageid = pages.keys()[0]
        if pageid == '-1':
            # page deleted / moved / whatever but not now..
            raise PageHaveNoRevisions(self)

        revisions = pages[pageid].get("revisions")
        if not revisions:
            # None, or there but empty
            # page deleted / moved / whatever but not now..
            raise PageHaveNoRevisions(self)

        for idx, item in enumerate(revisions):
            yield idx, self.HISTORY_CLASS.FromJSON(item)


    @defer.inlineCallbacks
    def search_valid_version(self, acceptance_days=7, _show_debug_info=False):
        """Search for a "good-enough" version of the page wanted.

        Where good-enough means:

         * Page version is commited by a registered user (being it
           human or bot).

         * Page version is commited by an unregistered user and stayed
           alive longer than 'acceptance_days'.

        Return None if no version page was found.

        For more info, check issue #124 at:
            http://code.google.com/p/cdpedia/issues/detail?id=124
        """
        self.acceptance_delta = datetime.timedelta(acceptance_days)
        idx, hist = yield self.iterate_history()
        if idx != 0:
            logger("Possible vandalism (idx=%d) in %r", idx, self.basename)
        defer.returnValue(self.get_revision_url(hist.page_rev_id))

    @defer.inlineCallbacks
    def iterate_history(self):
        prev_date = datetime.datetime.now()

        for history_size in [6, 100]:
            history = yield self.get_history(size=history_size)
            json_rev_history = json.loads(history)

            for idx, hist in self.iter_history_json(json_rev_history):
                if self.validate_revision(hist, prev_date):
                    defer.returnValue((idx, hist))
                prev_date = hist.date

        defer.returnValue((idx, hist))

    def validate_revision(self, hist_item, prev_date):
        # if the user is registered, it's enough for us! (even if it's a bot)
        if hist_item.user_registered:
            return True
        #if it's not registered, check for how long this version lasted
        if hist_item.date + self.acceptance_delta < prev_date:
            return True
        return False


regex = '(<h1 id="firstHeading" class="firstHeading" lang=".+">.+</h1>)(.+)\s*<div class="printfooter">'
capturar = re.compile(regex, re.MULTILINE|re.DOTALL).search
no_ocultas = re.compile('<div id="mw-hidden-catlinks".*?</div>',
                                                re.MULTILINE|re.DOTALL)
no_pp_report = re.compile("<!--\s*?NewPP limit report.*?-->",
                                                re.MULTILINE|re.DOTALL)


def extract_content(html, url):
    encontrado = capturar(html)
    if not encontrado:
        # unknown html format
        raise ValueError("El archivo %s posee un formato desconocido" % url)
    newhtml = "\n".join(encontrado.groups())

    # algunas limpiezas más
    newhtml = no_ocultas.sub("", newhtml)
    newhtml = no_pp_report.sub("", newhtml)

    return newhtml


@defer.inlineCallbacks
def get_html(url, basename):

    try:
        html = yield fetch_html(url)
    except error.Error as e:
        if e.status == http.NOT_FOUND:
            logger("HTML not found (404): %s", basename)
        else:
            logger("Try again (HTTP error %s): %s", e.status, basename)
        defer.returnValue(False)
    except Exception as e:
        logger("Try again (Exception while fetching: %r): %s", e, basename)
        defer.returnValue(False)

    if not html:
        logger("Got an empty file: %r", url)

    # ok, downloaded the html, let's check that it complies with some rules
    if "</html>" not in html:
        # we surely didn't download it all
        logger("Try again (unfinished download): %s", basename)
        defer.returnValue(False)
    try:
        html.decode("utf8")
    except UnicodeDecodeError:
        logger("Try again (not utf8): %s", basename)
        defer.returnValue(False)

    try:
        html = extract_content(html, url)
    except ValueError as e:
        logger("Try again (Exception while extracting content: %r): %s",
               e, basename)
        defer.returnValue(False)

    defer.returnValue(html)


def obtener_link_200_siguientes(html):
    links = re.findall('<a href="([^"]+)[^>]+>200 siguientes</a>',html)
    if links == []:
        return
    return '%s%s' % (WIKI[:-1], links[0])


def reemplazar_links_paginado(html, n):
    ''' Reemplaza lar urls anteriores y siguientes

        En el caso de la primera no encontrará el link 'anterior', no hay problema
        con llamar esta función
    '''

    def reemplazo(m):
        pre, link, post = m.groups()
        idx = '"' if (n==2 and delta==-1) else '_%d"'%(n+delta)
        return '<a href="/wiki/' + link.replace('_',' ') + idx + post

    # Reemplazo el link 'siguiente'
    delta = 1
    html = re.sub('(<a href="/w/index.php\?title=)(?P<link>[^&]+)[^>]+(>200 siguientes</a>)', reemplazo, html)

    # Reemplazo el link 'anterior'
    delta = -1
    return re.sub('(<a href="/w/index.php\?title=)(?P<link>[^&]+)[^>]+(>200 previas</a>)', reemplazo, html)

def get_temp_file(temp_dir):
    return tempfile.NamedTemporaryFile(suffix='.html',
                                       prefix='scrap-',
                                       dir=temp_dir,
                                       delete=False)

@defer.inlineCallbacks
def save_htmls(data_urls):
    """Save the article to a temporary file.

    If it is a category, process pagination and save all pages.
    """
    html = yield get_html(str(data_urls.url), data_urls.basename)
    if html is None:
        defer.returnValue(False)

    temp_file = get_temp_file(data_urls.temp_dir)

    if u"Categoría" not in data_urls.basename:
        # normal case, not Categories or any paginated stuff
        temp_file.write(html)
        temp_file.close()
        defer.returnValue([(temp_file, data_urls.disk_name)])

    temporales = []
    # cat!
    n = 1

    while True:

        if n == 1:
            temporales.append((temp_file, data_urls.disk_name))
        else:
            temporales.append((temp_file, data_urls.disk_name + '_%d' % n))

        # encontrar el link tomando url
        prox_url = obtener_link_200_siguientes(html)

        html = reemplazar_links_paginado(html, n)
        temp_file.write(html)
        temp_file.close()

        if not prox_url:
            defer.returnValue(temporales)

        html = yield get_html(prox_url.replace('&amp;','&'),
                              data_urls.basename)
        if html is None:
            defer.returnValue(False)

        temp_file = get_temp_file(data_urls.temp_dir)
        n += 1

@defer.inlineCallbacks
def fetch(data_urls, language):
    """Fetch a wikipedia page (that can be paginated)."""
    page = WikipediaArticle(language, data_urls.url, data_urls.basename)
    try:
        url = yield page.search_valid_version()
    except PageHaveNoRevisions:
        logger("Version not found: %s", data_urls.basename)
        defer.returnValue(False)
    except:
        logger.exception("ERROR while getting valid version for %r",
                         data_urls.url)
        defer.returnValue(False)
    data_urls = data_urls._replace(url=url)

    # save the htmls with the (maybe changed) url and all the data
    temporales = yield save_htmls(data_urls)

    # transform temp data into final files
    for temp_file, disk_name in temporales:
        try:
            os.rename(temp_file.name, disk_name.encode("utf-8"))
        except OSError as e:
            logger("Try again (Error creating file %r: %r): %s",
                   disk_name, e, data_urls.basename)
            defer.returnValue(False)

    # return True when it was OK!
    defer.returnValue(True)


class StatusBoard(object):

    def __init__(self, language):
        self.total = 0
        self.bien = 0
        self.mal = 0
        self.tiempo_inicial = time.time()
        self.language = language

    @defer.inlineCallbacks
    def process(self, data_urls):
        try:
            ok = yield fetch(data_urls, self.language)
        except Exception:
            self.total += 1
            self.mal += 1
            raise
        else:
            self.total += 1
            if ok:
                self.bien += 1
            else:
                self.mal += 1
        finally:
            velocidad = self.total / (time.time() - self.tiempo_inicial)
            sys.stdout.write("\rTOTAL=%d  BIEN=%d  MAL=%d  vel=%.2f art/s" %
                (self.total, self.bien, self.mal, velocidad))
            sys.stdout.flush()


@defer.inlineCallbacks
def main(nombres, language, dest_dir, pool_size=20):
    pool = workerpool.WorkerPool(size=int(pool_size))
    data_urls = URLAlizer(nombres, dest_dir, language)
    board = StatusBoard(language)
    yield pool.start(board.process, data_urls)
    print   # final new line for console aesthetic


USAGE = """
Usar: scraper.py <NOMBRES_ARTICULOS> <LANGUAGE> <DEST_DIR> [CONCURRENT]"
  Descarga la wikipedia escrapeándola.

  NOMBRES_ARTICULOS es un listado de nombres de artículos. Debe ser descargado
  y descomprimido de:
  http://download.wikipedia.org/eswiki/latest/eswiki-latest-all-titles-in-ns0.gz

  DEST_DIR es el directorio de destino, donde se guardan los artículos. Puede
  ocupar unos 40GB o más.

  CONCURRENT es la cantidad de corrutinas que realizan la descarga. Se puede
  tunear para incrementar velocidad de artículos por segundo. Depende mayormente
  de la conexión: latencia, ancho de banda, etc. El default es 20.

  Los nombres de los artículos que no pudieron descargarse correctamente se
  guardan en probar_de_nuevo.txt.

"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print USAGE
        sys.exit(1)

    d = main(*sys.argv[1:])
    d.addCallback(lambda _: reactor.stop())
    reactor.run()
