# Copyright 2017-2020 CDPedistas (see AUTHORS.txt)
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

"""Tests for the src.preprocessing.preprocessors module."""

import base64
import codecs

import config
from src.preprocessing.preprocessors import (
    ContentExtractor,
    VIPDecissor,
    VIPArticles,
    Length,
    OmitRedirects,
    HTMLCleaner,
    SCORE_VIP,
    extract_pages,
)
from .utils import load_test_article, FakeWikiFile

import pytest


@pytest.fixture
def article_1():
    """Load article html and wikifile."""
    return load_test_article('article_with_inlinemath')


@pytest.fixture
def article_2():
    """Load article html and wikifile."""
    return load_test_article('article_with_images')


cases = [('modelo que permite obtener un color', 'article_with_images'),
         ("15 de febrero de 1811", 'article_with_summary_fixed'),
         ("en el territorio continental. Se extiende", 'portal')]


@pytest.fixture(params=cases)
def article_3(request):
    """Load article html and wikifile."""
    text, article_name = request.param
    return text, load_test_article(article_name)


@pytest.fixture
def dummy_vip_decissor(mocker):
    """Dummy VIP decissor."""
    target = 'src.preprocessing.preprocessors.vip_decissor'

    def vip_decissor(title):
        return (title.startswith('A'), 1)

    mocker.patch(target, vip_decissor)


class TestContentExtractor:
    """Tests for ContentExtractor preprocessor."""

    @pytest.fixture
    def extractor(self, mocker, tmp_path):
        """Create a test ContentExtractor."""
        mocker.patch('config.LOG_TITLES', str(tmp_path / 'titles.txt'))
        return ContentExtractor()

    def test_output_open_close(self, extractor):
        """Check output file."""
        assert not extractor.output.closed
        extractor.close()
        assert extractor.output.closed

    def test_extract_title(self, extractor, article_2):
        """Test title extraction."""
        html, wikifile = article_2
        title = 'Síntesis aditiva de color'
        assert title in html
        result = extractor(wikifile)
        assert result == (0, [])
        assert extractor.stats['title found'] == 1
        extractor.close()
        assert extractor.output.closed
        with codecs.open(config.LOG_TITLES, 'r', encoding='utf-8') as fh:
            title_saved = next(fh).split(config.SEPARADOR_COLUMNAS)[1]
        assert title_saved == title

    def test_extract_paragraph(self, extractor, article_3):
        """Test paragraph extraction."""
        text, (html, wikifile) = article_3
        assert text in html
        result = extractor(wikifile)
        assert result == (0, [])
        assert extractor.stats['text found'] == 1
        extractor.close()
        assert extractor.output.closed
        with open(config.LOG_TITLES, 'r', encoding='utf-8') as fh:
            text_saved_b64 = next(fh).split(config.SEPARADOR_COLUMNAS)[2]
        text_saved = base64.b64decode(text_saved_b64).decode('utf-8')
        assert len(text_saved) <= extractor._max_length + 1  # text + ellipsis
        assert text in text_saved

    def test_extract_from_empty_article(self, extractor):
        """Test extraction from empty article."""
        wikifile = FakeWikiFile('<html><body></body></html>', url='url')
        result = extractor(wikifile)
        extractor.close()
        assert result == (0, [])
        assert extractor.stats['title not found'] == 1
        assert extractor.stats['text not found'] == 1
        expected_line = 'url|<no-title>|\n'
        with codecs.open(config.LOG_TITLES, 'r', encoding='utf-8') as fh:
            assert expected_line == next(fh)


class TestVIPDecissor:
    """Tests for VIPDecissor."""

    @pytest.fixture
    def vips(self, mocker, tmp_path):
        """Set expected VIP articles information."""
        mocker.patch('config.DIR_TEMP', str(tmp_path))

        # VIP articles from languages.yaml
        include = 'Wikipedia:Portal', 'Wikipedia:Acerca_de'
        langconf = {'include': include, 'portal_index': 'Portal:MainPortal'}
        mocker.patch('config.langconf', langconf, create=True)

        # VIP articles from  featured.txt
        featured = 'Big_bang', 'Río_de_la_Plata', 'Neutrón'
        mocker.patch('config.DESTACADOS', str(tmp_path / 'featured.txt'))
        with codecs.open(config.DESTACADOS, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(featured))

        # VIP articles from main portals page
        portals = ['Portal:Derecho', 'Portal:Economía', 'Portal:Educación']
        with (tmp_path / 'portal_pages.txt').open('wt', encoding='utf-8') as fh:
            for portal in portals:
                fh.write(portal + '\n')

        return dict(include=include, featured=featured, portals=portals)

    @pytest.fixture
    def vip_decissor(self, vips):
        """Create a test VIPDecissor."""
        return VIPDecissor()

    def test_vip_from_config(self, vips, vip_decissor):
        """Test VIP titles from languages.yaml config."""
        assert vip_decissor(vips['include'][0])
        assert vip_decissor(vips['include'][1])

    def test_vip_from_featured(self, vips, vip_decissor):
        """Test VIP titles from featured file."""
        assert vip_decissor(vips['featured'][0])
        assert vip_decissor(vips['featured'][1])
        assert vip_decissor(vips['featured'][2])

    def test_vip_from_portals(self, vips, vip_decissor):
        """Test VIP titles extracted from portals.html."""
        assert vip_decissor(vips['portals'][0])
        assert vip_decissor(vips['portals'][1])
        assert vip_decissor(vips['portals'][2])


class TestVIPArticles:
    """Tests for VIPArticles preprocessor."""

    @pytest.fixture
    def viparticles(self, dummy_vip_decissor):
        """Create a test VIPArticles."""
        return VIPArticles()

    def test_article_vip(self, viparticles):
        """Test score assigned to a VIP article."""
        wikifile = FakeWikiFile('', url='Argentina')
        result = viparticles(wikifile)
        assert result == (SCORE_VIP, [])
        assert viparticles.stats['vip'] == 1

    def test_article_normal(self, viparticles):
        """Test that a normal article is not scored."""
        wikifile = FakeWikiFile('', url='Spam')
        result = viparticles(wikifile)
        assert result == (0, [])
        assert viparticles.stats['normal'] == 1


class TestOmitRedirects:
    """Tests for OmitRedirects preprocessor."""

    @pytest.fixture
    def vip_redirect(self):
        """Americano is a redirect to América."""
        html = ('<div class="redirectMsg"><ul class="redirectText"><li>'
                '<a href="/wiki/Am%C3%A9rica">América</a></li></ul></div>')
        return FakeWikiFile(html, url='Americano')

    @pytest.fixture
    def normal_redirect(self):
        """Telegram.org is a redirect to Telegram."""
        html = ('<div class="redirectMsg"><ul class="redirectText"><li>'
                '<a href="/wiki/Telegram">Telegram</a></li></ul></div>')
        return FakeWikiFile(html, url='Telegram.org')

    @pytest.fixture
    def omit_redirects(self, mocker, tmp_path, dummy_vip_decissor):
        """Create a test OmitRedirects."""
        mocker.patch('config.LOG_REDIRECTS', str(tmp_path / 'redirects.txt'))
        return OmitRedirects()

    def test_no_redirect(self, omit_redirects, article_1):
        """Normal articles shouldn't be discarded."""
        _, wikifile = article_1
        result = omit_redirects(wikifile)
        assert result == (0, [])
        assert omit_redirects.stats['simplefile'] == 1

    def test_redirect_url(self, omit_redirects):
        """Redirect URL should be extracted from href attribute of link."""
        html = '<ul class="redirectText"><li><a href="/wiki/Foo_Bar">Foo Bar</a></li></ul>'
        wikifile = FakeWikiFile(html, url='url')
        omit_redirects(wikifile)
        omit_redirects.close()
        expected_line = 'url|Foo_Bar\n'
        with open(config.LOG_REDIRECTS, 'rt', encoding='utf-8') as fh:
            assert expected_line == next(fh)

    def test_save(self, normal_redirect, omit_redirects):
        """Test saved results."""
        omit_redirects(normal_redirect)
        omit_redirects.close()
        expected_line = 'Telegram.org' + config.SEPARADOR_COLUMNAS + 'Telegram' + '\n'
        with codecs.open(config.LOG_REDIRECTS, 'r', encoding='utf-8') as fh:
            assert expected_line == next(fh)

    def test_normal(self, normal_redirect, omit_redirects):
        """Test a redirect to a normal article."""
        result = omit_redirects(normal_redirect)
        assert result == (None, [])
        assert omit_redirects.stats['redirect'] == 1

    def test_vip(self, vip_redirect, omit_redirects):
        """Test a redirect to a VIP article."""
        result = omit_redirects(vip_redirect)
        assert result == (None, [('América', SCORE_VIP)])
        assert omit_redirects.stats['redirect'] == 1


class TestLength:
    """Tests for Length preprocessor."""

    @pytest.fixture
    def length(self):
        """Create a test Length."""
        return Length()

    def test_length(self, length):
        """Test correct length score."""
        html = '<html><body>abcd <p>foo bar baz</p> dcbá</body></html>'
        wikifile = FakeWikiFile(html)
        score, _ = length(wikifile)
        assert score == len(html)


class TestHTMLCleaner:
    """Tests for HTMLCleaner preprocessor."""

    @pytest.fixture
    def cleaner(self):
        """Create a test HTMLCleaner."""
        return HTMLCleaner()

    def test_remove_inlinemath(self, cleaner, article_1):
        """Test inlinemath cleaning."""
        html, wikifile = article_1
        text = 'MJX-TeXAtom-ORD'
        assert text in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text not in wikifile.get_html()

    def test_remove_img_srcset(self, cleaner, article_2):
        """Test removal of srcset attribute."""
        html, wikifile = article_2
        text = 'srcset="//upload.wikimedia.org/'
        assert text in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text not in wikifile.get_html()

    def test_remove_not_last_version_text(self, cleaner):
        """Test removal of unwanted text."""
        html = ('<div><div id="contentSub">\n<div class="mw-revision warningbox">'
                'spam spam spam\n</div> </div>foo bar</div>')
        html_fixed = '<div><div id="contentSub"></div>foo bar</div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_edit_section(self, cleaner):
        """Test removal of edit links."""
        html = ('<h2>Title<span class="mw-editsection">'
                '<span>[Edit]</span></span></h2>')
        html_fixed = '<h2>Title<span class="mw-editsection"></span></h2>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_ambox(self, cleaner):
        """Test removal of message boxes."""
        html = ('<table class="ambox ambox-content">'
                '<tr><td>Spam Spam</td></tr></table>')
        html_fixed = '<table class="ambox ambox-content"></table>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_links_keep_text(self, cleaner, article_2):
        """Test unwrapping of special links."""
        html, wikifile = article_2
        texts_keep = ('Discusión', 'Categoría')
        texts_remove = tuple(t[0] for t in HTMLCleaner.unwrap_links)
        assert all(text in html for text in texts_keep)
        assert all(text in html for text in texts_remove)
        result = cleaner(wikifile)
        assert result == (0, [])
        html_fixed = wikifile.get_html()
        assert all(text in html_fixed for text in texts_keep)
        assert not all(text in html_fixed for text in texts_remove)

    def test_remove_hidden_subtitle(self, cleaner):
        """Test removal of subtitle."""
        html = '<div><div id="siteSub">Spam Spam</div>foo bar</div>'
        html_fixed = '<div>foo bar</div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_jump_links(self, cleaner, article_2):
        """Test removal of unwanted jump links."""
        html, wikifile = article_2
        text1 = '<a class="mw-jump-link" href="#mw-head">'
        text2 = '<a class="mw-jump-link" href="#p-search">'
        assert text1 in html
        assert text2 in html
        result = cleaner(wikifile)
        assert result == (0, [])
        html_fixed = wikifile.get_html()
        assert text1 not in html_fixed
        assert text2 not in html_fixed

    def test_remove_inline_alerts(self, cleaner):
        """Test removal of inline alerts keeping similar looking references."""
        html = ('<p>Foo<sup>[<i><a href="link">spam spam<a></i>]</sup> '
                'bar<sup>[<a href="#cite_note-1">1</a>]</sup></p>')
        html_fixed = '<p>Foo bar<sup>[<a href="#cite_note-1">1</a>]</sup></p>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_printfooter(self, cleaner, article_2):
        """Test removal of print footer."""
        html, wikifile = article_2
        text = '<div class="printfooter">'
        assert text in html
        result = cleaner(wikifile)
        assert result == (0, [])
        assert text not in wikifile.get_html()

    def test_remove_hidden_categories(self, cleaner):
        """Test removal of hidden categories sections."""
        html = ('<div id="catlinks"><div id="mw-normal-catlinks">Foo</div>'
                '<div id="mw-hidden-catlinks">Spam</div></div>')
        html_fixed = '<div id="catlinks"><div id="mw-normal-catlinks">Foo</div></div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_comments(self, cleaner):
        """Test removal of HTML comments."""
        html = ('<div>foo<!--spam spam--></div>'
                '<div>bar</div><!--\nspam\nspam\nspam\n-->')
        html_fixed = '<div>foo</div><div>bar</div>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()

    def test_remove_parsing_errors(self, cleaner):
        """Test removal of wikipedia parsing error notices."""
        html = '<p>Foo<span class="error mw-ext-cite-error" lang="es">Spam Spam</span> bar</p>'
        html_fixed = '<p>Foo bar</p>'
        wikifile = FakeWikiFile(html)
        result = cleaner(wikifile)
        assert result == (0, [])
        assert html_fixed in wikifile.get_html()


class TestExtractPages:
    """Tests for the extract_pages function."""

    def test_extract_link(self):
        """Normal links to wiki pages must be extracted."""
        html = '<a href="/wiki/N%C3%BAmero_natural" title="Número natural">número natural</a>'
        wikifile = FakeWikiFile(html)
        links = extract_pages(wikifile.soup)
        assert list(links) == ['Número_natural']

    def test_extract_portal_link_normal(self):
        """Links to portal pages must be extracted."""
        html = ('<a href="/wiki/Portal:Exploraci%C3%B3n_espacial" '
                'title="Portal:Exploración espacial">Exploración espacial</a>')
        wikifile = FakeWikiFile(html)
        links = extract_pages(wikifile.soup)
        assert list(links) == ['Portal:Exploración_espacial']

    def test_extract_portal_link_redirect(self):
        """Redirection links to portal pages must be extracted."""
        html = ('<a href="/wiki/Portal:Astron%C3%A1utica" class="mw-redirect" '
                'title="Portal:Astronáutica">Astronáutica</a>')
        wikifile = FakeWikiFile(html)
        links = extract_pages(wikifile.soup)
        assert list(links) == ['Portal:Astronáutica']

    def test_skip_by_class(self):
        """Don't extract links of some class."""
        html = ('<a href="/wiki/foo" class="image"><img src="url" /></a>'
                '<a class="internal" href="/wiki/foo" title="foo">foo</a>')
        wikifile = FakeWikiFile(html)
        links = extract_pages(wikifile.soup)
        assert len(list(links)) == 0

    def test_skip_non_wiki_urls(self):
        """Don't extract links without a '/wiki/' prefix."""
        html = '<a href="/nowiki/foo">foo</a>'
        wikifile = FakeWikiFile(html)
        links = extract_pages(wikifile.soup)
        assert list(links) == []

    def test_remove_link_fragment(self):
        """Remove fragment from page URL."""
        html = '<a href="/wiki/foo#bar">foobar</a>'
        wikifile = FakeWikiFile(html)
        links = extract_pages(wikifile.soup)
        assert list(links) == ['foo']
