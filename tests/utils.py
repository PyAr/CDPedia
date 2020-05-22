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
# For further info, check  http://code.google.com/p/cdpedia/

from __future__ import unicode_literals

import codecs
import os

import bs4


class FakeWikiFile:
    """Emulate a simplified WikiFile object."""

    def __init__(self, html, url='url'):
        self.soup = bs4.BeautifulSoup(html, features='html.parser')
        self.url = url

    @property
    def html(self):
        """Return unicode representation of current soup."""
        return self.soup.decode()


def load_fixture(filename):
    """Load a fixture from disk."""
    filepath = os.path.join(os.getcwd(), 'tests', 'fixtures', filename)
    with codecs.open(filepath, "r", encoding='utf-8') as fh:
        return fh.read()


def load_test_article(name):
    """Return HTML content and FakeWikiFile instance of article."""
    if not name.endswith('.html'):
        name = name + '.html'
    html = load_fixture(name)
    wikifile = FakeWikiFile(html)
    return html, wikifile

