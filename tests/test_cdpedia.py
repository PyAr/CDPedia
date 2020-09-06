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

import cdpedia
import config

import pytest


@pytest.fixture
def language_config(mocker, tmp_path):
    """Dummy language configuration."""
    mocker.patch('config.LANGUAGE', None)
    mocker.patch('config.LANGUAGE_FILE', str(tmp_path / 'language.txt'))


def test_load_language(language_config):
    """Test correct loading of language from file."""
    assert config.LANGUAGE is None
    with open(config.LANGUAGE_FILE, 'wt', encoding='utf-8') as fh:
        fh.write('es\n')
    cdpedia.load_language()
    assert config.LANGUAGE == 'es'


def test_load_language_no_file(language_config):
    """Do nothing if language file is not present."""
    assert config.LANGUAGE is None
    cdpedia.load_language()
    assert config.LANGUAGE is None
