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

import datetime
import functools
import gzip
import itertools
import json
import logging
import os
import re
import StringIO
import sys
import tempfile
import time
import urllib

from functools import partial

from twisted.internet import defer, reactor
from twisted.web import client, error, http

import to3dirs
import workerpool

# log all bad stuff
_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("scraper.log")
_logger.addHandler(handler)
formatter = logging.Formatter("%(asctime)s  %(message)s")
handler.setFormatter(formatter)
logger = functools.partial(_logger.log, logging.INFO)

WIKI = 'http://es.wikipedia.org/'

USER_AGENT = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.10) '\
             'Gecko/20100915 Ubuntu/10.04 (lucid) Firefox/3.6.10'

REQUEST_HEADERS = {'Accept-encoding':'gzip'}


class URLAlizer(object):
    def __init__(self, listado_nombres, dest_dir):
        self.dest_dir = dest_dir
        self.temp_dir = dest_dir + ".tmp"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.fh = open(listado_nombres, 'r')

        # saltea la primera linea
        prim_linea = self.fh.readline()
        assert prim_linea.strip() == "page_title"

    def next(self):
        while True:
            line = self.fh.readline()
            if line == "":
                raise StopIteration
            basename = line.decode("utf-8").strip()
            path = os.path.join(self.dest_dir, to3dirs.to_path(basename))
            disk_name = os.path.join(path, to3dirs.to_filename(basename))
            if not os.path.exists(disk_name.encode('utf-8')):
                if not os.path.exists(path.encode('utf-8')):
                    os.makedirs(path.encode('utf-8'))

                temp_file = tempfile.NamedTemporaryFile(suffix=".html",
                              prefix="scrap-", dir=self.temp_dir, delete=False)
                quoted_url = urllib.quote(basename.encode('utf-8'))
                # Skip wikipedia automatic redirect
                url = u"%sw/index.php?title=%s&redirect=no" % (WIKI, quoted_url)
                return url, self.temp_dir, disk_name, self, basename

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
            print "\n===== Error", repr(url), err, repr(err)
            if isinstance(err, error.Error) and err.status == http.NOT_FOUND:
                raise
            retries -= 1
            if not retries:
                raise


compose_funcs = lambda f,g: (lambda x: f(g(x)))


class WikipediaWebBase:
    @staticmethod
    def URL_ENC(preurl):
        return preurl.replace(' ', '_')

    @staticmethod
    def QUOTE(*args):
        conv = lambda s: s if type(s)==type('') else s.encode('utf-8')
        return tuple(map(compose_funcs(urllib.quote, conv), args))


class WikipediaUser(WikipediaWebBase):
    """
    Given a user-id or a line of a wikipedia-page's history, create the
    asociated user.

    It will be able to answer (by querying the web) if it's a bot, a registered
    user or none of them (ie: an anonymouse user).
    """
    USUARIO_RE = re.compile('title="Usuario\:([^"]*)"')
    CONTRIB_RE = re.compile('title="Especial\:([^"]*)"')
    NO_USER_PAGE_YET = u' (aún no redactado)'
    BotDict = {}

    @classmethod
    def FromJSON(cls, jsonitem):
        userid = jsonitem.get('userid',0)
        user = jsonitem.get('user','hidden')
        return WikipediaUser(user, userid!=0)

    def __init__(self, userid, registered):
        self.has_page = not userid.endswith(self.NO_USER_PAGE_YET)

        if self.has_page:
            self.userid = userid
        else:
            self.userid = userid[:-len(self.NO_USER_PAGE_YET)]

        self.registered = registered # False=anonymous
        if not registered or not self.has_page:
            # Assume that if the user have no page defined,
            # it shouldn't be not a robot..
            self.BotDict[self.userid]=False

    def __str__(self):
        return '<id:%s registered:%s bot:%s>'%(self.userid, self.registered, self.is_bot())

    @property
    def user_url(self):
        if not self.has_page:
            return None
        preurl = 'http://es.wikipedia.org/wiki/Usuario:%s'
        return self.URL_ENC( preurl % self.QUOTE(self.userid) )

    @staticmethod
    def url_to_relative(url):
        globaldomain = 'wikipedia.org'
        assert globaldomain in url
        return url.split(globaldomain, 1)[1]

    @property
    def _is_bot(self):
        return self.BotDict.get(self.userid)

    @defer.inlineCallbacks
    def is_bot(self):
        if self._is_bot is None:
            yield self._check_botness()
        defer.returnValue(self._is_bot)

    def is_anonymous(self):
        return not self.registered

    @defer.inlineCallbacks
    def _check_botness(self):
        user_info_page = yield fetch_html(self.bot_check_url)
        self._is_bot = self.url_to_relative(self.user_url) in user_info_page
        self.BotDict[self.userid] = self._is_bot
        defer.returnValue(self._is_bot)

    @property
    def bot_check_url(self):
        preurl = 'http://es.wikipedia.org/w/index.php?' \
                 'title=Especial:ListaUsuarios&group=bot&limit=1&username=%s'
        return self.URL_ENC( preurl % self.QUOTE(self.userid) )


class PageHaveNoRevisions(Exception):
    pass


class WikipediaPage(WikipediaWebBase):
    """Represent a wikipedia page.

    It should know how to retrive the asociated history page and any revision.
    """
    #these should be setup by a localized subclass
    HISTORY_BASE = None
    HISTORY_CLASS = None
    REVISION_URL = None

    def __init__(self, url, basename):
        self.url = url
        self.basename = basename
        self._history = None
        self.history_size = 6

    def __str__(self):
        return '<wp: %s>' % (self.basename.encode('utf-8'),)

    @property
    def history_url(self):
        return self.URL_ENC( self.HISTORY_BASE % ( self.history_size, self.QUOTE(self.basename)[0] ) )

    def get_revision_url(self, revision=None):
        """
        Return the revision url when revision is provided, elsewhere the basic
        url for the page
        """
        if revision is None:
            return self.url
        return self.URL_ENC(self.REVISION_URL % self.QUOTE(self.basename, revision))

    @defer.inlineCallbacks
    def get_history(self, size=6):
        if self._history is None or size!=self.history_size:
            self.history_size = size
            self._history = yield fetch_html(self.history_url)
        defer.returnValue(self._history)

    def iter_history_json(self, json_rev_history):
        pages = json_rev_history['query']['pages']
        pageid = pages.keys().pop()
        if (pageid==-1 or not pages[pageid].has_key("revisions") or
            (len(pages[pageid]['revisions'])==0)):
            # page deleted / moved / whatever but not now..
            raise PageHaveNoRevisions(self)

        for idx, item in enumerate(pages[pageid]['revisions']):
            yield idx, self.HISTORY_CLASS.FromJSON(self, item)


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
        if hist_item.user.registered:
            return True
        #if it's not registered, check for how long this version lasted
        if hist_item.date + self.acceptance_delta < prev_date:
            return True
        return False


class WikipediaPageHistoryItem:
    def __init__(self, page, user, page_rev_id, date):
        self.page = page
        self.user = user
        self.page_rev_id = page_rev_id
        self.date = date

    @classmethod
    def FromJSON(cls, page, jsonitem):
        user = WikipediaUser.FromJSON(jsonitem)
        page_rev_id = str(jsonitem['revid'])
        date = cls._get_page_version_date_json(jsonitem)
        return cls(page, user, page_rev_id, date)

    @classmethod
    def _get_page_version_date_json(cls, jsonitem):
        """
        # 2012-04-08T18:48:45Z
        Returns the version date if found, None if not
        """
        r = re.compile("([0-9]*)-([0-9]*)-([0-9]*)T([0-9]*):([0-9]*):([0-9]*)Z")
        m = r.match(jsonitem['timestamp'])
        if m:
            year, month, day, hour, minute, second = m.groups()
            tdate = tuple([int(x) for x in (year, month, day, hour, minute)])
            return datetime.datetime(*tdate)

    def __str__(self):
        return '<rev: by %s id %r %r>'%(self.user, self.page_rev_id, self.date)


class WikipediaPageHistoryItemES (WikipediaPageHistoryItem):
    PAGE_VERSION_ID = re.compile('.*<a href="([^"]*)" title="[^"]*">act</a>.*')
    PAGE_VERSION_DATE = re.compile(
                       '.*>([0-9]*):([0-9]*) ([0-9]*) ([a-z]*) ([0-9]*)</a>.*')
    COMMENT_RE = re.compile('<span class="comment">([^]]*)')
    ID_RE = re.compile(".*oldid=([0-9]*).*")
    MONTH_NAMES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago',
                    'sep', 'oct', 'nov', 'dic']


class WikipediaPageES(WikipediaPage):
    REVISION_URL = 'http://es.wikipedia.org/w/index.php?title=%s&oldid=%s'
    HISTORY_BASE = 'http://es.wikipedia.org/w/api.php?action=query&prop=revisions&format=json&rvprop=ids|timestamp|user|userid&rvlimit=%d&titles=%s'
    HISTORY_CLASS =  WikipediaPageHistoryItemES


regex = '(<h1 id="firstHeading" class="firstHeading">.+</h1>)(.+)\s*<!-- /catlinks -->'
capturar = re.compile(regex, re.MULTILINE|re.DOTALL).search
no_ocultas = re.compile('<div id="mw-hidden-catlinks".*?</div>',
                                                re.MULTILINE|re.DOTALL)
no_pp_report = re.compile("<!--\s*?NewPP limit report.*?-->",
                                                re.MULTILINE|re.DOTALL)


def extract_content(html, url):
    encontrado = capturar(html)
    if not encontrado:
        # Si estamos acá, el html tiene un formato diferente.
        # Por el momento queremos que se sepa.
        raise ValueError, "El archivo %s posee un formato desconocido" % url
    newhtml = "\n".join(encontrado.groups())

    # algunas limpiezas más
    newhtml = no_ocultas.sub("", newhtml)
    newhtml = no_pp_report.sub("", newhtml)

    return newhtml

@defer.inlineCallbacks
def fetch(datos):
    url, temp_file, disk_name, uralizer, basename = datos
    page = WikipediaPageES(url, basename)
    try:
        url = yield page.search_valid_version()
    except PageHaveNoRevisions:
        logger("Version not found: %s", basename)
        defer.returnValue(False)
    except:
        _logger.exception("ERROR while getting valid version for %r", url)
        defer.returnValue(False)

def get_html(url, basename):
    ''' Returns the html of an article.

        If an error occurs returns None
    '''

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

    return html

def find_next_page_link(html):
    ''' Returns the link for the next page

        If there is no next page, returns None
    '''
    links = re.findall('<a href="([^"]+)[^>]+>200 siguientes</a>',html)
    if links == []:
        defer.returnValue(False)
    return '%s%s' % (WIKI[:-1], links[0])

def replace_previous_and_next_links(html, n):
    ''' Replace the links

        In the case of the first page, will not find the previous link, but
        this does not break the regex behaivor
    '''

    def replace(m):
        # Be care about the delta 'global' param
        pre, link, post = m.groups()
        idx = '"' if (n==2 and delta=-1) else '_%d"'%(n+delta)
        return '<a href="/wiki/' + link.replace('_',' ') + idx + post

    # Replace 'next' link
    delta = 1
    html = re.sub('(<a href="/w/index.php\?title=)(?P<link>[^&]+)[^>]+(>200 siguientes</a>)',
                  replace, html)

    # Replace 'previous' link
    delta = -1
    return re.sub('(<a href="/w/index.php\?title=)(?P<link>[^&]+)[^>]+(>200 previas</a>)',
                  replace, html)

def get_temp_file(temp_dir):
    return tempfile.NamedTemporaryFile(suffix='.html',
                                       prefix='scrap-',
                                       dir=temp_dir,
                                       delete=False)

def save_htmls(datos):
    ''' Save to a temporary file the article,

        If it is a category, process pagination and save all pages
    '''
    url, temp_dir, disk_name, _, basename = datos

    html = get_html(url, basename)
    if html is None:
        return

    temp_file = get_temp_file(temp_dir)

    if u"Categoría" not in basename:
        # normal case, not Categories or any paginated stuff
        with temp_file as fh:
            fh.write(html)

        return [(temp_file, disk_name)]

    temporales = []
    # cat!
    n = 1

    while True:

        idx = '' if (n == 1) else '_%d' % n
        temporales.append((temp_file, disk_name + idx))

        prox_url = find_next_page_link(html)

        html = replace_previous_and_next_links(html, n)

        if not prox_url:
            with temp_file as fh:
                fh.write(html)
            return temporales

        with temp_file as fh:
            fh.write(html)

        html = get_html(prox_url.replace('&amp;','&'), basename)
        if html is None:
            return temporales

        temp_file = get_temp_file(temp_dir)
        n += 1

def fetch(datos):
    url, temp_dir, disk_name, uralizer, basename = datos
    page = WikipediaPageES(url, basename)
    url = page.search_valid_version()
    if url is None:
        logger("Version not found: %s", basename)
        return

    temporales = save_htmls(datos)

    for temp_file, disk_name in temporales:
        try:
            os.rename(temp_file.name, disk_name.encode("utf-8"))
        except OSError as e:
            logger("Try again (Error creating file %r: %r): %s",
                   disk_name, e, basename)
            return

    # return True when it was OK!
    defer.returnValue(True)


class StatusBoard(object):

    def __init__(self):
        self.total = 0
        self.bien = 0
        self.mal = 0
        self.tiempo_inicial = time.time()

    @defer.inlineCallbacks
    def process(self, datos):
        ok = yield fetch(datos)
        self.total += 1
        if ok:
            self.bien += 1
        else:
            self.mal += 1

        velocidad = self.total / (time.time() - self.tiempo_inicial)
        sys.stdout.write("\rTOTAL=%d  BIEN=%d  MAL=%d  vel=%.2f art/s" %
                         (self.total, self.bien, self.mal, velocidad))
        sys.stdout.flush()


@defer.inlineCallbacks
def main(nombres, dest_dir, pool_size=20):
    pool = workerpool.WorkerPool(size=int(pool_size))
    urls = URLAlizer(nombres, dest_dir)
    board = StatusBoard()
    yield pool.start(board.process, urls)


USAGE = """
Usar: scraper.py <NOMBRES_ARTICULOS> <DEST_DIR> [CONCURRENT]"
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
    if len(sys.argv) < 3:
        print USAGE
        sys.exit(1)

    d = main(*sys.argv[1:])
    d.addCallback(lambda _: reactor.stop())
    reactor.run()
