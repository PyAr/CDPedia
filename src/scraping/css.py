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

"""CSS stylesheets scraping.

Wikipedia uses a modular system for requesting stylesheets. The CSS links
in the article's HTML contain params that request multiple individual CSS
modules, based on the content of the page that needs to be styled: tables,
TOC, image galleries, quotes, infoboxes, etc.

The article scraper extracts and saves all raw CSS links in a single file.
This module will parse that file and download all individual CSS modules,
saving each one to its own file.

Additionally, each CSS module may contain links to other media resources
needed for styling content, like icons and backgrounds. These files will
also be downloaded.

Finally, a unified stylesheet will be generated, concatenating all CSS
modules into a single file that will be loaded by all CDPedia pages.

Reference: https://www.mediawiki.org/wiki/API:Styling_content
"""

import html
import logging
import functools
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
    """Download CSS modules with media resources and create a unified stylesheet."""
    scraper = _CSSScraper(cssdir)
    scraper.download_all()
    unified_css = os.path.join(cssdir, config.CSS_FILENAME)
    scraper.unify_stylesheets(unified_css)


class URLNotFoundError(Exception):
    """Error while fetching a css resource."""
    def __init__(self, msg, *msg_args):
        super().__init__(msg)
        self.msg_args = msg_args


class _CSSScraper:
    """Download required stylesheets and associated media resources.

    Details of the process:

    - Load raw CSS links from CSS_LINKS_FILENAME.
    - Parse all raw CSS links to extract a set of unique CSS module names.
    - Check which CSS modules have been already downloaded. Parse those that
      exist to collect links to media resources (they will be downloaded later).
    - Download missing CSS modules, save each one to its own file. Parse the
      CSS before saving to continue collecting media resources links.
    - Download all media resources, save them in a single folder using a safe
      filename.
    - Generate a unified stylesheet by combining all single CSS modules.
    - All links to external media resources will be retargeted to the local
      versions if they exist
    """

    # known URLs found in CSS that are not media resources and shouldn't be altered
    urls_no_media = (
        'http://www.w3.org/1998/Math/MathML',  # MathML namespace
    )

    def __init__(self, cssdir):
        self.cssdir = cssdir
        self.resdir = os.path.join(cssdir, config.CSS_RESOURCES_DIRNAME)
        self.modules = {}  # css modules
        self.resources = {}  # media files (no css)

        # url and params for downloading stylesheets
        self.url = config.URL_WIKIPEDIA + 'w/load.php'
        self.params = {'only': 'styles', 'skin': 'vector', 'lang': config.LANGUAGE}
        self.known_errors = [URLNotFoundError]

        # url retargeter to be used when generating unified stylehseet
        self.retarget_urls = functools.partial(re_resource_url.sub, self._retarget_url)
        # base location for retargeting CSS media resources (relative to final assets dir)
        self.retarget_base = '/static/{}/{}/'.format(
            config.CSS_DIRNAME, config.CSS_RESOURCES_DIRNAME)

    def download_all(self):
        """Download required css files and associated resources."""
        self._load_modules_info()
        previous_count, items = 0, []
        # download missing css modules
        for i in self.modules.values():
            if i['is_file']:
                previous_count += 1
            else:
                items.append(i)

        logger.info('Scraping %i CSS modules', len(items))
        utiles.pooled_exec(self._download_css, previous_count, items, pool_size=20,
                           known_errors=self.known_errors)

        # download missing media resources
        os.makedirs(self.resdir, exist_ok=True)
        previous_count = 0
        items = []
        for i in self.resources.values():
            if i['is_file']:
                previous_count += 1
            else:
                items.append(i)

        logger.info('Scraping %i CSS media resources', len(items))
        utiles.pooled_exec(self._download_resource, previous_count, items, pool_size=20,
                           known_errors=self.known_errors)

    def _load_modules_info(self):
        """Load information about all CSS modules needed by CDPedia."""
        for name in self._module_names():
            url = self._css_url(name)
            filepath = os.path.join(self.cssdir, name)
            is_file = os.path.isfile(filepath)
            if is_file:
                # parse CSS module code to extract links to media resources,
                # they will be downloaded later if needed
                with open(filepath, 'rt', encoding='utf-8') as fh:
                    self._collect_resources_info(fh.read())
            self.modules[name] = {'url': url, 'filepath': filepath, 'is_file': is_file}

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
            url = urllib.parse.urlparse(html.unescape(link))
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
            if url in self.urls_no_media:
                continue
            # build absolute url if needed
            if url.startswith('//'):
                url = 'http:' + url
            elif url.startswith('/'):
                url = config.URL_WIKIPEDIA + url[1:]
            name = self._safe_resource_name(url)
            filepath = os.path.join(self.resdir, name)
            is_file = os.path.isfile(filepath)
            self.resources[url_orig] = {'url': url, 'filepath': filepath, 'is_file': is_file}

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
            item['is_file'] = True
            # collect resources urls for downloading them later
            self._collect_resources_info(css)
            with open(item['filepath'], 'wt', encoding='utf-8') as fh:
                fh.write(css)

    def _download_resource(self, item):
        """Download a single resource."""
        res = self._download(item['url'])
        if res:
            item['is_file'] = True
            with open(item['filepath'], 'wb') as fh:
                fh.write(res)

    def _retarget_url(self, match):
        """Retarget external media URL to local file if available.

        E.g.: 'url(http://wiki.org/foo/bar.png)' -> 'url(/css/images/bar.png)'.
        Meant to be used as 'repl' param for 're.sub'.
        """
        url_raw = match.group(1)
        resource = self.resources.get(url_raw)
        if url_raw in self.urls_no_media:
            # don't alter special URLs
            url = url_raw
        elif not resource or not resource['is_file']:
            # don't keep original URL to avoid browser requests to the web
            url = ''
            logger.debug('No local version of %s', url_raw)
        else:
            # retarget
            filename = os.path.basename(resource['filepath'])
            url = self.retarget_base + filename
        return 'url({})'.format(url)

    def unify_stylesheets(self, output):
        """Unify all CSS modules into a single stylesheet.

        The unified CSS will have all external links retargeted to local files if
        they exist. Otherwise links will be removed to prevent unwanted web requests.
        """
        logger.info("Generating unified stylesheet '%s' with retargeted links",
                    config.CSS_FILENAME)
        with open(output, 'wt', encoding='utf-8') as fh_main:
            for module in self.modules.values():
                if module['is_file']:
                    with open(module['filepath'], 'rt', encoding='utf-8') as fh:
                        css_raw = fh.read()
                    css_fixed = self.retarget_urls(css_raw)
                    fh_main.write(css_fixed)
                    fh_main.write('\n')
