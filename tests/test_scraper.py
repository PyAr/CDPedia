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

"""Tests for the article scraper."""

import pytest

import config
from src.scraping.scraper import CSSLinksExtractor
from tests.utils import load_test_article


class TestCSSLinksExtractor:
    """Tests for the CSS links extractor."""

    @pytest.fixture
    def css_params(self, tmp_path):
        cssdir = tmp_path / config.CSS_DIRNAME
        cssdir.mkdir()
        linksfile = cssdir / config.CSS_LINKS_FILENAME
        return str(tmp_path), linksfile

    def test_match_css_links(self, css_params):
        """Match all CSS links in HTML."""
        langdir, _ = css_params
        extractor = CSSLinksExtractor(langdir)
        html, _ = load_test_article('article_with_images')
        links = extractor._findlinks(html)
        assert len(links) == 4

    def test_init_without_previous_data(self, css_params):
        """Set the correct defaults."""
        langdir, _ = css_params
        extractor = CSSLinksExtractor(langdir)
        assert extractor.links == set()
        assert not extractor._fh.closed

    def test_init_with_previous_data(self, css_params):
        """Load previously saved URLs."""
        langdir, linksfile = css_params
        links = {'eggs/bacon', 'spam'}
        linksfile.write_text('\n'.join(links) + '\n')
        extractor = CSSLinksExtractor(langdir)
        assert extractor.links == links
        assert not extractor._fh.closed

    def test_closing_filehandler(self, css_params):
        """Correctly close filehandler."""
        langdir, _ = css_params
        extractor = CSSLinksExtractor(langdir)
        assert not extractor._fh.closed
        extractor.close()
        assert extractor._fh.closed

    def test_extracting_css_links(self, css_params):
        """Extract all CSS links from HTML and save them to file."""
        langdir, linksfile = css_params
        extractor = CSSLinksExtractor(langdir)
        html, _ = load_test_article('article_with_images')
        extractor(html)
        assert len(extractor.links) == 4
        extractor.close()
        links = linksfile.read_text(encoding='utf-8')
        assert len(links.split()) == 4
