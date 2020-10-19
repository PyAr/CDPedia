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

import urllib.parse

import pytest

import config
from src.scraping.css import re_resource_url, scrap_css, _LinkExtractor, _Scraper, _Joiner
from tests.utils import load_test_article


@pytest.mark.parametrize('url', (
    'https://foo.bar/baz',
    '//foo.bar/baz',
    '/foo.bar/baz',
    '"/foo.bar(baz)"',
    '"/foo"bar"(baz)"',
    '/foo(bar)baz'
    '/foo/bar/baz.png?1234',
))
def test_re_resource_url(url):
    """Match external resources URLs in CSS files."""
    css = '#p-lang {{background: transparent url({}) no-repeat center top;}}'.format(url)
    assert re_resource_url.search(css).group(1) == url


def test_scrap_css(mocker):
    """Do scraping and joining when calling scrap_css."""
    mocker.patch('src.scraping.css.link_extractor')
    scraper = mocker.Mock()
    mocker.patch('src.scraping.css._Scraper', scraper)
    joiner = mocker.Mock()
    mocker.patch('src.scraping.css._Joiner', joiner)
    mocker.patch('src.scraping.css.link_extractor.cssdir', 'outdir')
    scrap_css()
    assert scraper.mock_calls[-1] == mocker.call().scrap()
    assert joiner.mock_calls[-1] == mocker.call().join('outdir')


class TestLinkExtractor:
    """Tests for the CSS links extractor."""

    def test_match_css_links(self):
        """Match all CSS links in HTML."""
        html, _ = load_test_article('article_with_images')
        findlinks = _LinkExtractor()._findlinks
        links = findlinks(html)
        assert len(links) == 4

    def test_setup_without_previous_data(self, tmp_path):
        """Set the correct defaults."""
        extractor = _LinkExtractor()
        cssdir = str(tmp_path)
        extractor.setup(cssdir)
        assert extractor.cssdir == cssdir
        assert extractor.links == set()
        assert not extractor._fh.closed

    def test_setup_with_previous_data(self, tmp_path):
        """Load previously saved URLs in setup."""
        link = 'foo/bar'
        (tmp_path / config.CSS_LINKS_FILENAME).write_text(link + '\n')
        extractor = _LinkExtractor()
        cssdir = str(tmp_path)
        extractor.setup(cssdir)
        assert extractor.cssdir == cssdir
        assert extractor.links == {link}
        assert not extractor._fh.closed

    def test_closing_filehandler(self, tmp_path):
        """Correctly close filehandler."""
        extractor = _LinkExtractor()
        extractor.setup(str(tmp_path))
        assert not extractor._fh.closed
        extractor.close()
        assert extractor._fh.closed

    def test_extracting_css_links(self, tmp_path):
        """Extract all CSS links from HTML."""
        extractor = _LinkExtractor()
        extractor.setup(str(tmp_path))
        html, _ = load_test_article('article_with_images')
        extractor(html)
        assert len(extractor.links) == 4
        extractor.close()
        links = (tmp_path / config.CSS_LINKS_FILENAME).read_text(encoding='utf-8')
        assert len(links.split()) == 4


class TestScraper:
    """Test for the CSS scraper."""

    @pytest.fixture
    def scraper(self, mocker, tmp_path):
        """Scraper instance with minimal params."""
        mocker.patch('config.URL_WIKIPEDIA', 'http://xy.wiki.org/')
        return _Scraper(set(), str(tmp_path))

    def test_scrap(self, mocker, scraper):
        """Donwload CSS and resources."""
        pooled_exec = mocker.Mock()
        mocker.patch('src.utiles.pooled_exec', pooled_exec)
        scraper.scrap()
        calls = pooled_exec.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == scraper._download_css
        assert calls[1][0][0] == scraper._download_resource

    @pytest.mark.parametrize('module_exists', (True, False))
    def test_get_modules_info(self, mocker, tmp_path, scraper, module_exists):
        """Construct module info."""
        name = 'foo.bar'
        mocker.patch.object(scraper, '_module_names', lambda: {name})
        mocker.patch.object(scraper, '_extract_resources_info')
        filepath = tmp_path / 'foo.bar.css'
        if module_exists:
            filepath.touch()
        scraper._get_modules_info()
        module = scraper.modules.get(name)
        assert module
        assert name in module['url']
        assert module['filepath'] == str(filepath)
        assert module['exists'] == module_exists

    def test_module_names(self, scraper):
        """Extract module names from raw url."""
        links = {
            'wiki.com/foo?a=b&modules=first.module&c=d',
            'wiki.com/foo?n=r&modules=first.module|second.module&x=y',
            'wiki.com/foo?f=g&modules=foo.bar,baz&h=i'
        }
        scraper.links = links
        names = scraper._module_names()
        assert names == {'first.module', 'second.module', 'foo.bar', 'foo.baz'}

    def test_build_css_url(self, mocker, scraper):
        """Build URL for downloading a css module."""
        module_name = 'foo.bar_baz'
        url = urllib.parse.urlparse(scraper._css_url(module_name))
        assert url.netloc == 'xy.wiki.org'
        assert url.path == '/w/load.php'
        query_params = {'modules': module_name, **scraper.params}
        for k, v in query_params.items():
            assert '{}={}'.format(k, v) in url.query

    def test_extract_resources_info(self, scraper):
        """Extract multiple resources links from css."""
        css = 'foo url(link1) bar url(link2) baz'
        scraper._extract_resources_info(css)
        assert set(scraper.resources) == {'link1', 'link2'}

    @pytest.mark.parametrize('urls', (
        ('"foo/bar.baz"', 'foo/bar.baz'),
        ('//foo/bar.baz', 'http://foo/bar.baz'),
        ('"//foo/bar.baz"', 'http://foo/bar.baz'),
        ('"/foo/bar.baz"', 'http://xy.wiki.org/foo/bar.baz'),
        ('/foo/bar.baz', 'http://xy.wiki.org/foo/bar.baz'),
        ('foo/bar.baz', 'foo/bar.baz'),
        ('http://foo/bar.baz', 'http://foo/bar.baz'),
    ))
    def test_extract_resources_info_url(self, mocker, scraper, urls):
        """Construct full resource URL after extraction."""
        url_raw, url_expected = urls
        mocker.patch.object(scraper, '_safe_resource_name', lambda _: 'foo')
        css = 'background: lightblue url({}) no-repeat fixed center;'.format(url_raw)
        scraper._extract_resources_info(css)
        assert scraper.resources['foo']['url'] == url_expected

    @pytest.mark.parametrize('url_name', (
        ('https://foo/bar/fooボ.ico', 'foo.ico'),
        ('http://foo/bar/foo.png?1234', 'foo.png'),
        ('http://foo/bar/%23foóo%2A.jpg', '#foo*.jpg'),
    ))
    def test_safe_resource_name(self, url_name):
        url, name_expected = url_name
        assert _Scraper._safe_resource_name(url) == name_expected

    @pytest.mark.parametrize('decode_resp', (True, False))
    def test_download(self, mocker, scraper, decode_resp):
        """Get correct kind of response."""
        asset = b'foo'
        resp_expected = 'foo' if decode_resp else b'foo'
        headers = mocker.Mock(get_content_charset=lambda: 'utf-8')
        resp = mocker.Mock(read=lambda: asset, headers=headers)
        mocker.patch('urllib.request.urlopen', lambda req: resp)
        resp = scraper._download('http://spam', decode=decode_resp)
        assert resp == resp_expected

    def test_download_css(self, mocker, tmp_path, scraper):
        """Donwload and save a css module."""
        filepath = tmp_path / 'foo.css'
        mocker.patch.object(scraper, '_download', return_value='foo')
        item = {'url': 'url', 'filepath': str(filepath)}
        scraper._download_css(item)
        assert item['exists']
        assert filepath.read_text() == 'foo'

    def test_download_resource(self, mocker, tmp_path, scraper):
        """Download and save a css resource."""
        filepath = tmp_path / 'foo.png'
        mocker.patch.object(scraper, '_download', return_value=b'foo')
        item = {'url': 'url', 'filepath': str(filepath)}
        scraper._download_resource(item)
        assert item['exists']
        assert filepath.read_bytes() == b'foo'


class TestJoiner:
    """Tests for the CSS joiner."""

    @pytest.fixture
    def resources(self):
        resources = {
            'foo': {'url_raw': 'url_raw_foo', 'url': 'urlfoo', 'exists': True},
            'bar': {'url_raw': 'url_raw_bar', 'url': 'urlbar', 'exists': True},
            'baz': {'url_raw': 'url_raw_baz', 'url': 'urlbaz', 'exists': False},
        }
        return resources

    def test_load_resources(self, resources):
        """Load only existing resources for retargeting URLs."""
        joiner = _Joiner(None, resources)
        assert joiner.resources == {'url_raw_foo': 'foo', 'url_raw_bar': 'bar'}

    def test_join(self, tmp_path):
        """Test joining css modules."""
        modules = {
            'foo': {'filepath': tmp_path / 'foo.css', 'exists': True},
            'bar': {'filepath': tmp_path / 'bar.css', 'exists': True},
            'baz': {'filepath': tmp_path / 'baz.css', 'exists': False},
        }
        modules['foo']['filepath'].write_text('foo-content')
        modules['bar']['filepath'].write_text('bar-content')
        joiner = _Joiner(modules, {})
        joiner.join(outdir=str(tmp_path))
        output = tmp_path / config.CSS_FILENAME
        assert output.read_text(encoding='utf-8') == 'foo-content\nbar-content\n'

    def test_fix_url(self, resources):
        """Retarget url to local files."""
        css = 'spam url(url_raw_foo) spam url(url_raw_bar) spam url(url_raw_baz) spam'
        joiner = _Joiner({}, resources)
        css_fixed = re_resource_url.sub(joiner._fix_url, css)
        assert 'url(/static/css/images/foo)' in css_fixed
        assert 'url(/static/css/images/bar)' in css_fixed
        assert 'url(nofile)' in css_fixed  # no local 'baz'

    def test_dont_fix_url(self, resources):
        """Don't fix preselected URLs, e.g. XML namespaces."""
        css = 'spam url(url_raw_foo) spam url(url_raw_bar) spam'
        joiner = _Joiner({}, resources)
        joiner._dont_fix = {'url_raw_foo'}
        css_fixed = re_resource_url.sub(joiner._fix_url, css)
        assert 'url(url_raw_foo)' in css_fixed
        assert 'url(/static/css/images/bar)' in css_fixed
