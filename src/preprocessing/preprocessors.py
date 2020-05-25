#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2006-2020 CDPedistas (see AUTHORS.txt)
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
# For further info, check  https://github.com/PyAr/CDPedia/

"""
Functions to generate page rankings. All of them receive a WikiPage
as argument.

Another function will then handle the algorithm to produce the final
sorting of the pages, taking the subtotals calculated here as reference.

Processors must not touch the result of WikiSite to prevent loss of
control over its value and the consequent undesired appearance of spurious
pages at the end.

Each processor returns two things: the score of the page it processes
and a list of (other_page, score) tuples in case it assigns a score to
other pages. If a processor wants to omit a given page, it must return
None instead of the score.
"""

import base64
import collections
import logging
import os
import re
from urllib.parse import unquote

import bs4

import config

SCORE_VIP = 100000000  # 1e8
SCORE_PEISHRANC = 5000

logger = logging.getLogger(__name__)


class _Processor(object):
    """Generic processor, don't use directly, thoght to be subclassed."""

    def __init__(self):
        self.name = 'Generic processor'
        self.stats = None

    def __call__(self, wikifile):
        """Apply preprocessor to a WikiFile instance.

        Example:
          return (123456, [])
        """
        raise NotImplementedError

    def close(self):
        """Close operations, save stuff if needed.

        Overwrite only if necessary.
        """


class ContentExtractor(_Processor):
    """Extract content from the HTML to be used later."""

    # max length of the text extracted from the article
    _max_length = 230

    def __init__(self):
        super(ContentExtractor, self).__init__()
        self.name = "ContentExtractor"
        self.output = open(config.LOG_TITLES, "at", encoding="utf-8")
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        soup = bs4.BeautifulSoup(wikifile.html, "lxml")

        # extract the title
        node = soup.find('h1')
        if node is None:
            title = "<no-title>"
            self.stats['title not found'] += 1
        else:
            title = node.text.strip()
            self.stats['title found'] += 1

        # extract the first parragraph
        node = soup.find('p')
        if node is None:
            safe_text = ''
            self.stats['text not found'] += 1
        else:
            text = node.text.strip()
            if len(text) > self._max_length:
                text = text[:self._max_length] + "..."
            safe_text = base64.b64encode(text.encode("utf8"))
            self.stats['text found'] += 1

        # dump to disk
        line = config.SEPARADOR_COLUMNAS.join((wikifile.url, title, safe_text))
        self.output.write(line + '\n')
        return (0, [])

    def close(self):
        """Close output."""
        self.output.close()


class VIPDecissor(object):
    """Hold those VIP articles that must be included."""

    def __init__(self):
        self._vip_articles = None

    def _load(self):
        """Load all needed special articles.

        This is done not at __init__ time because some of this are dynamically
        generated files, so doesn't need to happen at import time.
        """
        viparts = self._vip_articles = set()

        # some manually curated pages
        if config.DESTACADOS is not None:
            with open(config.DESTACADOS, 'rt', encoding='utf8') as fh:
                for line in fh:
                    viparts.add(line.strip())

        # must include according to the config
        viparts.update(config.langconf['include'])

        # those portals articles from the front-page portal
        fname = os.path.join(config.DIR_ASSETS, 'dynamic', 'portals.html')
        if os.path.exists(fname):
            re_link = re.compile(r'<a.*?href="/wiki/(.*?)">', re.MULTILINE | re.DOTALL)
            with open(fname, 'rb') as fh:
                mainpage_portals_content = fh.read()
            for link in re_link.findall(mainpage_portals_content):
                viparts.add(unquote(link).decode('utf8'))
        logger.info("Loaded %d VIP articles", len(viparts))

    def __call__(self, article):
        if self._vip_articles is None:
            self._load()
        return article in self._vip_articles


vip_decissor = VIPDecissor()


class VIPArticles(_Processor):
    """A processor for articles that *must* be included."""

    def __init__(self):
        super(VIPArticles, self).__init__()
        self.name = "VIPArticles"
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        if vip_decissor(wikifile.url):
            self.stats['vip'] += 1
            score = SCORE_VIP
        else:
            self.stats['normal'] += 1
            score = 0
        return (score, [])


class OmitRedirects(_Processor):
    """Process and omit redirects from compilation."""

    def __init__(self):
        super(OmitRedirects, self).__init__()
        self.name = "Redirects"
        self.output = open(config.LOG_REDIRECTS, "a", encoding="utf-8")
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        soup = bs4.BeautifulSoup(wikifile.html, "lxml")
        node = soup.find('ul', 'redirectText')
        if not node:
            # not a redirect, simple file
            self.stats['simplefile'] += 1
            return (0, [])

        # store the redirect in corresponding file
        self.stats['redirect'] += 1
        url_redirect = node.text
        sep_col = config.SEPARADOR_COLUMNAS
        line = wikifile.url + sep_col + url_redirect + "\n"
        self.output.write(line)

        # if redirect was very important, transmit this feature
        # to destination article
        if vip_decissor(wikifile.url):
            trans = [(url_redirect, SCORE_VIP)]
        else:
            trans = []

        # return None for the redirect itself to be discarded
        return (None, trans)

    def close(self):
        """Close output."""
        self.output.close()


class Peishranc(_Processor):
    """Calculate the peishranc.

    Register how many times a page is referred by the rest of the pages.
    Ignore self-references and duplicates.

    NOTE: In case of any change in this class, please run the test cases from
    the tests directory.
    """

    def __init__(self):
        super(Peishranc, self).__init__()
        self.name = "Peishranc"

        # Capture href and class attributes of `a` tags in corresponding named groups.
        self.capture = re.compile(r'<a href="/wiki/(?P<href>[^"#]*).*?'
                                  r'(?:class="(?P<class>.[^"]*)"|.*?)+>')
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        scores = {}
        for link in self.capture.finditer(wikifile.html):
            data = link.groupdict()

            # discard by class and by link start
            class_ = data['class']
            if class_ in ('image', 'internal'):
                continue

            # decode and unquote
            lnk = unquote(data['href'])

            # "/" are not really stored like that in disk, they are replaced
            # by the SLASH word
            lnk = lnk.replace("/", "SLASH")

            scores[lnk] = scores.get(lnk, 0) + 1

        # remove "self-praise"
        if wikifile.url in scores:
            del scores[wikifile.url]

        # factor score by constant
        for lnk, score in list(scores.items()):
            scores[lnk] = score * SCORE_PEISHRANC

        return (0, list(scores.items()))


class Length(_Processor):
    """Score the page based on its length (html)."""

    def __init__(self):
        super(Length, self).__init__()
        self.name = "Length"

    def __call__(self, wikifile):
        length = len(wikifile.html)
        return (length, [])


class HTMLCleaner(_Processor):
    """Remove different HTML parts or sections."""

    # if the first column found in a link, replace it by its text (keeping stats
    # using the second column)
    unwrap_links = [
        ('redlink', 'redlink'),
        ('action=edit', 'editlinks'),
        ('Especial:Categor', 'category'),
    ]

    def __init__(self):
        super(HTMLCleaner, self).__init__()
        self.name = "HTMLCleaner"
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        soup = bs4.BeautifulSoup(wikifile.html, features='html.parser')

        # remove text and links of 'not last version'
        tag = soup.find('div', id='contentSub')
        if tag is not None:
            tag.clear()
            self.stats['notlastversion'] += 1

        # remove edit section
        sections = soup.find_all('span', class_="mw-editsection")
        self.stats['edit_sections'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove ambox (reference needed) section
        sections = soup.find_all('table', class_="ambox")
        self.stats['ambox'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove inline math
        sections = soup.find_all('span', class_="mwe-math-mathml-inline")
        self.stats['inline_math'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove srcset attribute from img tags
        sections = soup.find_all('img', srcset=True)
        self.stats['img_srcset'] += len(sections)
        for tag in sections:
            tag.attrs.pop('srcset')

        # remove some links (but keeping their text)
        for a_tag in soup.find_all('a'):
            try:
                href = a_tag['href']
            except KeyError:
                # no link
                continue

            for searchable, stat_key in self.unwrap_links:
                if searchable in href:
                    # special link, keep stat and replace it by the text
                    self.stats[stat_key] += 1
                    a_tag.unwrap()
                    break

        # remove hidden subtitle
        tag = soup.find('div', id='siteSub')
        if tag is not None:
            tag.extract()
            self.stats['hidden_subtitle'] += 1

        # remove toc jump link
        tag = soup.find('a', class_='mw-jump-link', href='#mw-head')
        if tag is not None:
            tag.extract()
            self.stats['jump_links'] += 1

        # remove search jump link
        tag = soup.find('a', class_='mw-jump-link', href='#p-search')
        if tag is not None:
            tag.extract()
            self.stats['jump_links'] += 1

        # remove inline alerts (bracketed superscript with italic text)
        for tag in soup.find_all('sup'):
            children = tag.children
            try:
                if next(children) == '[' and next(children).name == 'i':
                    tag.extract()
                    self.stats['inline_alerts'] += 1
            except StopIteration:
                continue

        # remove printfooter
        tag = soup.find('div', class_='printfooter')
        if tag is not None:
            tag.extract()
            self.stats['print_footer'] += 1

        # remove hidden categories section
        for tag in soup.find_all('div', id='mw-hidden-catlinks'):
            tag.extract()
            self.stats['hidden_categories'] += 1

        # remove comments
        for tag in soup(text=True):
            if isinstance(tag, bs4.Comment):
                tag.extract()
                self.stats['comments'] += 1

        # remove mediawiki parsing error red notices
        for tag in soup('span', class_='error'):
            tag.extract()
            self.stats['parsing_error_notices'] += 1

        # fix original html and return no score at all
        wikifile.html = str(soup)
        return (0, [])


# Classes that will be used for preprocessing each page,
# in execution order.
ALL = [
    HTMLCleaner,
    VIPArticles,
    OmitRedirects,
    Peishranc,
    Length,
    ContentExtractor,
]
