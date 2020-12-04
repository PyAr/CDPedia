#!/usr/bin/env python

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
from urllib.parse import unquote

import bs4

import config

SCORE_VIP = 100000000  # 1e8
SCORE_PEISHRANC = 5000

# prefix used for pages
PAGES_PREFIX = '/wiki/'

logger = logging.getLogger(__name__)


class _Processor:
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
        # extract the title
        node = wikifile.soup.find('h1')
        if node is None:
            title = "<no-title>"
            self.stats['title not found'] += 1
        else:
            title = node.text.strip()
            self.stats['title found'] += 1

        # extract the first paragraph
        safe_text = ''
        parent = wikifile.soup.find('div', class_="mw-parser-output")
        if parent is not None:
            node = parent.find('p', class_=None, recursive=False)
            if node is None or len(node.text.split()) < 2:
                cand = parent.find_all('p', class_=None)[:4]
                if cand:
                    length = [len(n.text.split()) for n in cand]
                    which = length.index(max(length))
                    node = cand[which]

            if node is not None:
                text = node.text.strip()
                if len(text) > self._max_length:
                    text = text[:self._max_length] + "…"
                safe_text = base64.b64encode(text.encode("utf8")).decode('utf-8')

        if safe_text == '':
            self.stats['text not found'] += 1
        else:
            self.stats['text found'] += 1

        # dump to disk
        line = config.SEPARADOR_COLUMNAS.join((wikifile.url, title, safe_text))
        self.output.write(line + '\n')
        return (0, [])

    def close(self):
        """Close output."""
        self.output.close()


class VIPDecissor:
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

        # portal articles from the front-page portal, itself included
        viparts.add(config.langconf['portal_index'])
        _path = os.path.join(config.DIR_TEMP, 'portal_pages.txt')
        with open(_path, 'rt', encoding='utf-8') as fh:
            viparts.update(line.strip() for line in fh)

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
        self.output = open(config.LOG_REDIRECTS, "at", encoding="utf-8")
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        node = wikifile.soup.find('ul', 'redirectText')
        if not node:
            # not a redirect, simple file
            self.stats['simplefile'] += 1
            return (0, [])

        # store the redirect in corresponding file
        self.stats['redirect'] += 1
        # extract target from href not from text
        url_redirect = node.find('a').attrs['href']
        # remove path prefix
        if url_redirect.startswith(PAGES_PREFIX):
            url_redirect = url_redirect[len(PAGES_PREFIX):]
        url_redirect = unquote(url_redirect)

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


def extract_pages(soup):
    """Extract the link to pages from a soup."""
    prefix_length = len(PAGES_PREFIX)

    for a_tag in soup.find_all('a', href=True):

        # discard by class
        if any(c in ('image', 'internal') for c in a_tag.get('class', '')):
            continue

        # discard by href start
        href = a_tag.get('href')
        if not href.startswith(PAGES_PREFIX):
            continue

        # discard prefix and fragment part
        link = href[prefix_length:].split('#', 1)[0]

        # unquote
        link = unquote(link)

        yield link


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
        self.stats = collections.Counter()

    def __call__(self, wikifile):
        scores = {}
        for link in extract_pages(wikifile.soup):
            scores[link] = scores.get(link, 0) + 1

        # remove "self-praise"
        if wikifile.url in scores:
            del scores[wikifile.url]

        # factor score by constant
        for link, score in scores.items():
            scores[link] = score * SCORE_PEISHRANC

        return (0, list(scores.items()))


class Length(_Processor):
    """Score the page based on its length (html)."""

    def __init__(self):
        super(Length, self).__init__()
        self.name = "Length"

    def __call__(self, wikifile):
        length = wikifile.original_html_length
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
        # remove text and links of 'not last version'
        tag = wikifile.soup.find('div', id='contentSub')
        if tag is not None:
            tag.clear()
            self.stats['notlastversion'] += 1

        # remove edit section
        sections = wikifile.soup.find_all('span', class_="mw-editsection")
        self.stats['edit_sections'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove ambox (reference needed) section
        sections = wikifile.soup.find_all('table', class_="ambox")
        self.stats['ambox'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove inline math
        sections = wikifile.soup.find_all('span', class_="mwe-math-mathml-inline")
        self.stats['inline_math'] += len(sections)
        for tag in sections:
            tag.clear()

        # remove srcset attribute from img tags
        sections = wikifile.soup.find_all('img', srcset=True)
        self.stats['img_srcset'] += len(sections)
        for tag in sections:
            tag.attrs.pop('srcset')

        # remove some links (but keeping their text)
        for a_tag in wikifile.soup.find_all('a'):
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
        tag = wikifile.soup.find('div', id='siteSub')
        if tag is not None:
            tag.extract()
            self.stats['hidden_subtitle'] += 1

        # remove jump links shown at start of article
        for a_tag in wikifile.soup.find_all('a', class_='mw-jump-link', href=True):
            if a_tag['href'] in ('#p-search', '#mw-head', '#searchInput', '#mw-sidebar-button'):
                a_tag.extract()
                self.stats['jump_links'] += 1

        # remove inline alerts (bracketed superscript with italic text)
        for tag in wikifile.soup.find_all('sup'):
            children = tag.children
            try:
                if next(children) == '[' and next(children).name == 'i':
                    tag.extract()
                    self.stats['inline_alerts'] += 1
            except StopIteration:
                continue

        # remove printfooter
        tag = wikifile.soup.find('div', class_='printfooter')
        if tag is not None:
            tag.extract()
            self.stats['print_footer'] += 1

        # remove hidden categories section
        for tag in wikifile.soup.find_all('div', id='mw-hidden-catlinks'):
            tag.extract()
            self.stats['hidden_categories'] += 1

        # remove comments
        for tag in wikifile.soup(text=True):
            if isinstance(tag, bs4.Comment):
                tag.extract()
                self.stats['comments'] += 1

        # remove mediawiki parsing error red notices
        for tag in wikifile.soup('span', class_='error'):
            tag.extract()
            self.stats['parsing_error_notices'] += 1

        # return no score at all
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
