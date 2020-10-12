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

"""Tests for the 'compresor' module."""

import urllib.parse

import config
from src.armado.compresor import ArticleManager

import pytest


@pytest.mark.parametrize('filename', ('foobar', 'Fóõ_Bàr', 'foo%2Fbar', 'foo%2Ebar', 'foo%25bar'))
def test_redirects(mocker, tmp_path, filename):
    """Check that redirects are correctly registered in article block."""

    mocker.patch('config.DIR_BLOQUES', str(tmp_path))
    mocker.patch('config.LOG_REDIRECTS', str(tmp_path / 'redirects.txt'))
    mocker.patch('src.armado.compresor.Comprimido')
    top_pages = [('f/o/o', filename, 10)]
    mocker.patch('src.preprocessing.preprocess.pages_selector', mocker.Mock(top_pages=top_pages))

    title = urllib.parse.unquote(filename)  # only should unquote special filesystem chars
    with open(config.LOG_REDIRECTS, 'w', encoding='utf-8') as fh:
        fh.write('spam|{}\n'.format(title))

    _, tot_archs, tot_redirs = ArticleManager.generar_bloques('es', None)
    assert tot_archs == 1
    assert tot_redirs == 1
