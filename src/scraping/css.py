# Copyright 2020 CDPedistas (see AUTHORS.txt)
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

"""CSS stylesheets scraping."""

import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import config
from src import utiles
from src.scraping.pydocs import HEADERS

logger = logging.getLogger(__name__)

# regex matching links from the 'url' function in CSS code
re_resource_url = re.compile(r'url\(([^\s}]+)\)')


def scrap_css(cssdir):
    """Download CSS modules with associated resources and create a unified stylesheet."""
    # scrap stylesheets
    scraper = _CSSScraper(cssdir)
    scraper.download_all()
    # TODO: join css into single stylesheet


class URLNotFoundError(Exception):
    """Error while fetching a css resource."""
    def __init__(self, msg, *msg_args):
        super().__init__(msg)
        self.msg_args = msg_args


class _CSSScraper:
    """Download required stylesheets and associated resources."""

    def __init__(self, cssdir):
        self.cssdir = cssdir
        self.resdir = os.path.join(cssdir, config.CSS_RESOURCES_DIRNAME)
        self.modules = {}
        self.resources = {}

        # url and params for downloading stylesheets
        self.url = config.URL_WIKIPEDIA + 'w/load.php'
        self.params = {'only': 'styles', 'skin': 'vector', 'lang': config.LANGUAGE}
        self.known_errors = [URLNotFoundError]

    def download_all(self):
        """Download required css files and associated resources."""
        self._load_modules_info()

        # download missing css modules
        items = [i for i in self.modules.values() if not i['exists']]
        logger.info('Scraping %i CSS modules', len(items))
        utiles.pooled_exec(self._download_css, items, pool_size=20,
                           known_errors=self.known_errors)

        # download missing resources
        os.makedirs(self.resdir, exist_ok=True)
        items = [i for i in self.resources.values() if not i['exists']]
        logger.info('Scraping %i CSS associated resources', len(items))
        utiles.pooled_exec(self._download_resource, items, pool_size=20,
                           known_errors=self.known_errors)

    def _load_modules_info(self):
        """Load information about all CSS modules that must be downloaded."""
        for name in self._module_names():
            url = self._css_url(name)
            filepath = os.path.join(self.cssdir, name)
            exists = os.path.isfile(filepath)
            if exists:
                # stylesheet may contain resources not yet downloaded
                with open(filepath, 'rt', encoding='utf-8') as fh:
                    self._collect_resources_info(fh.read())
            self.modules[name] = {'url': url, 'filepath': filepath, 'exists': exists}

    def _module_names(self):
        """Extract unique module names from raw CSS links.

        Module names are specified in the 'modules' param of the query part of the link.
        E.g. value 'foo.bar,baz|a.b.c' contains 'foo.bar', 'foo.baz' and 'a.b.c' names.
        """
        # load raw css links collected while scraping articles
        links_file = os.path.join(self.cssdir, config.CSS_LINKS_FILENAME)
        with open(links_file, 'rt', encoding='utf-8') as fh:
            raw_links = [line.strip() for line in fh]

        unique_names = set()
        for link in raw_links:
            url = urllib.parse.urlparse(link)
            query = dict(urllib.parse.parse_qsl(url.query))
            names = query.get('modules')
            if not names:
                continue
            for name in names.split('|'):
                if ',' in name:
                    # 'foo.bar,baz' -> 'foo.bar', 'foo.baz'
                    first, *extra = name.split(',')
                    unique_names.add(first)
                    parent, _ = first.rsplit('.', 1)
                    for e in extra:
                        unique_names.add(parent + '.' + e)
                else:
                    # 'foo.bar.baz'
                    unique_names.add(name)
        logger.info('Found %i unique CSS module names', len(unique_names))
        return unique_names

    def _css_url(self, module_name):
        """Build URL for downloading a single css module."""
        query = urllib.parse.urlencode({'modules': module_name, **self.params})
        return self.url + '?' + query

    def _collect_resources_info(self, css):
        """Extract resources information from given css string."""
        for url_orig in re_resource_url.findall(css):
            url = url_orig.strip('"')
            # build absolute url if needed
            if url.startswith('//'):
                url = 'http:' + url
            elif url.startswith('/'):
                url = config.URL_WIKIPEDIA + url[1:]
            name = self._safe_resource_name(url)
            filepath = os.path.join(self.resdir, name)
            exists = os.path.isfile(filepath)
            self.resources[url_orig] = {'url': url, 'filepath': filepath, 'exists': exists}

    @staticmethod
    def _safe_resource_name(url):
        """Construct a safe filename from resource URL."""
        filename = os.path.basename(url)
        filename = urllib.parse.unquote(filename)
        filename = filename.encode("ascii", errors='ignore').decode("ascii")
        filename = filename.split("?")[0]  # remove trailing version, e.g. 'asd.png?123'
        return filename

    def _download(self, url, decode=False):
        """Donwload the specified item."""
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            resp = urllib.request.urlopen(req)
            asset = resp.read()
        except urllib.error.HTTPError as err:
            if err.code == 404:
                raise URLNotFoundError(url)
            raise
        if decode:
            enc = resp.headers.get_content_charset()
            return asset.decode(enc)
        return asset

    def _download_css(self, item):
        """Download a single CSS module."""
        css = self._download(item['url'], decode=True)
        if css:
            item['exists'] = True
            # collect resources urls for downloading them later
            self._collect_resources_info(css)
            with open(item['filepath'], 'wt', encoding='utf-8') as fh:
                fh.write(css)

    def _download_resource(self, item):
        """Download a single resource."""
        res = self._download(item['url'])
        if res:
            item['exists'] = True
            with open(item['filepath'], 'wb') as fh:
                fh.write(res)
