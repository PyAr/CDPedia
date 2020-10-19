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

import functools
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

import config
from src import utiles
from src.scraping.pydocs import HEADERS

logger = logging.getLogger(__name__)

# regex matching links from the 'url' CSS function
re_resource_url = re.compile(r'url\(([^\s}]+)\)')


class _LinkExtractor:
    """Collect CSS stylesheet links from the HTML source code."""

    def __init__(self):
        self.cssdir = None
        self.links = None

        # pattern for extracting css links from html
        regex = r"/w/load.php\?.*?only=styles&amp;skin=vector"
        self._findlinks = re.compile(regex).findall

        # lock for writing to same file from different threads
        self._lock = threading.Lock()

    def setup(self, cssdir):
        """Set output file handler and load previously saved data."""
        self.cssdir = cssdir
        links_file = os.path.join(cssdir, config.CSS_LINKS_FILENAME)
        try:
            self._fh = open(links_file, 'r+t', encoding='utf-8', buffering=1)
            self.links = set(line.strip() for line in self._fh)
        except FileNotFoundError:
            self._fh = open(links_file, 'wt', encoding='utf-8', buffering=1)
            self.links = set()

    def close(self):
        """Close output file handler."""
        self._fh.close()

    def __call__(self, html):
        """Extract css links from html string."""
        new_links = set(self._findlinks(html)).difference(self.links)
        if new_links:
            self.links.update(new_links)
            # as html head is discarded after this extraction,
            # dump new links as soon as found to avoid data loss
            with self._lock:
                self._fh.write('\n'.join(new_links) + '\n')


# single link collector for all scraping tasks: portals, articles, extra, etc.
link_extractor = _LinkExtractor()


def scrap_css():
    """Scrap CSS modules with associated resources and generate a single stylesheet."""
    # scrap stylesheets
    cssdir = link_extractor.cssdir
    scraper = _Scraper(link_extractor.links, cssdir)
    link_extractor.close()
    scraper.scrap()
    # combine all css into single file retargeting urls
    joiner = _Joiner(scraper.modules, scraper.resources)
    joiner.join(cssdir)


class URLNotFoundError(Exception):
    """Error while fetching a css resource."""
    def __init__(self, msg, *msg_args):
        super().__init__(msg)
        self.msg_args = msg_args


class _Scraper:
    """Scrap required stylesheets and associated resources."""

    def __init__(self, links, cssdir):
        self.links = links
        self.cssdir = cssdir
        self.resdir = os.path.join(cssdir, config.CSS_RESOURCES_DIRNAME)
        self.modules = {}
        self.resources = {}
        # url and params for downloading stylesheets
        self.url = config.URL_WIKIPEDIA + 'w/load.php'
        self.params = {'only': 'styles', 'skin': 'vector', 'lang': config.LANGUAGE}

    def scrap(self):
        """Scrap required css files and associated resources."""
        self._get_modules_info()
        known_errors = [URLNotFoundError]

        # scrap missing modules
        items = [i for i in self.modules.values() if not i['exists']]
        logger.info('Scraping %i CSS modules', len(items))
        utiles.pooled_exec(self._download_css, items, pool_size=20,
                           known_errors=known_errors)
        # scrap missing resources
        os.makedirs(self.resdir, exist_ok=True)
        items = [i for i in self.resources.values() if not i['exists']]
        logger.info('Scraping %i CSS associated resources', len(items))
        utiles.pooled_exec(self._download_resource, items, pool_size=20,
                           known_errors=known_errors)

    def _get_modules_info(self):
        """Get information about all CSS modules that should be downloaded."""
        for name in self._module_names():
            url = self._css_url(name)
            filepath = os.path.join(self.cssdir, name + '.css')
            exists = os.path.isfile(filepath)
            if exists:
                # stylesheet may contain resources not yet downloaded
                with open(filepath, 'rt', encoding='utf-8') as fh:
                    self._extract_resources_info(fh.read())
            self.modules[name] = {'url': url, 'filepath': filepath, 'exists': exists}

    def _module_names(self):
        """Extract unique module names from raw CSS links."""
        unique_names = set()
        for link in self.links:
            url = urllib.parse.urlparse(link)
            query = urllib.parse.parse_qs(url.query)
            names = query.get('modules')[0]
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

    def _extract_resources_info(self, css):
        """Extract resources information from css."""
        for url_raw in re_resource_url.findall(css):
            url = url_raw.strip('"')
            # build absolute url if needed
            if url.startswith('//'):
                url = 'http:' + url
            elif url.startswith('/'):
                url = config.URL_WIKIPEDIA + url[1:]
            name = self._safe_resource_name(url)
            filepath = os.path.join(self.resdir, name)
            exists = os.path.isfile(filepath)
            self.resources[name] = {'url': url, 'url_raw': url_raw,
                                    'filepath': filepath, 'exists': exists}

    def _safe_resource_name(self, url):
        """Construct a safe filename from given URL."""
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
            self._extract_resources_info(css)
            with open(item['filepath'], 'wt', encoding='utf-8') as fh:
                fh.write(css)

    def _download_resource(self, item):
        """Download a single resource."""
        res = self._download(item['url'])
        if res:
            item['exists'] = True
            with open(item['filepath'], 'wb') as fh:
                fh.write(res)


class _Joiner:
    """Generate a single stylesheet from all available CSS files."""

    def __init__(self, modules, resources):
        self.modules = modules
        self.resources = {v['url_raw']: k for k, v in resources.items() if v['exists']}
        # css resources relative path for web app
        self._res_dir = '/{}/{}/{}/'.format(
            config.STATIC_DIRNAME, config.CSS_DIRNAME, config.CSS_RESOURCES_DIRNAME)
        self._fix_urls = functools.partial(re_resource_url.sub, self._fix_url)

    def join(self, outdir):
        """Unify all CSS modules into a single stylesheet."""
        logger.info("Generating unified '%s' and retargeting links", config.CSS_FILENAME)
        output = os.path.join(outdir, config.CSS_FILENAME)
        with open(output, 'wt', encoding='utf-8') as fh_main:
            for m in self.modules.values():
                if m['exists']:
                    with open(m['filepath'], 'rt', encoding='utf-8') as fh:
                        css_fixed = self._fix_urls(fh.read())
                    fh_main.write(css_fixed)
                    fh_main.write('\n')

    def _fix_url(self, match):
        """Retarget resource link to local file if available."""
        url_raw = match.group(1)
        filename = self.resources.get(url_raw)
        if not filename:
            url_local = 'nofile'
            logger.debug('No local version of %s', url_raw)
        else:
            url_local = self._res_dir + filename
        return 'url({})'.format(url_local)
