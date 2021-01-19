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

import textwrap
import pytest

from src.web.test_infra import TEST_INFRA_FILENAME, load_test_infra_data, parse_test_infra_file


@pytest.fixture
def test_infra_file(mocker, tmp_path):
    content = """
        [es]
        Portal:Portada # Check page looks OK
        República_Agentina # Article with 'Argentina' title is shown
        # this comment should be ignored
        Satélites_de_Saturno

        [fr]
        Château # Image galleries shouldn't overflow

        [ay]
    """
    filepath = tmp_path / TEST_INFRA_FILENAME
    filepath.write_text(textwrap.dedent(content).strip(), encoding='utf-8')
    mocker.patch('config.LANGUAGE', 'es')
    return str(filepath)


def test_parsing_test_infra_file_items_number(test_infra_file):
    """All non empty lines not starting by '#' should be a page to check."""
    data = parse_test_infra_file(test_infra_file)
    assert len(data) == 3


def test_parsing_test_infra_file_read_name_and_check(test_infra_file):
    """Article name and check to do should be loaded in a tuple."""
    data = parse_test_infra_file(test_infra_file)
    name = 'Portal:Portada'
    check = 'Check page looks OK'
    assert (name, check) in data


def test_parsing_test_infra_file_read_empty_check(test_infra_file):
    """No check after title should be interpreted as None."""
    data = parse_test_infra_file(test_infra_file)
    name = 'Satélites_de_Saturno'
    assert (name, None) in data


def test_parsing_test_infra_file_load_other_language(mocker, test_infra_file):
    """All non empty lines not starting by '#' should be a page to check."""
    mocker.patch('config.LANGUAGE', 'fr')
    data = parse_test_infra_file(test_infra_file)
    assert data == [('Château', "Image galleries shouldn't overflow")]


def test_parsing_test_infra_file_not_existing_section(mocker, test_infra_file):
    """Return empty list if section not found."""
    mocker.patch('config.LANGUAGE', 'xy')
    data = parse_test_infra_file(test_infra_file)
    assert data == []


def test_parsing_test_infra_file_empty_section(mocker, test_infra_file):
    """Return empty list if section is empty."""
    mocker.patch('config.LANGUAGE', 'ay')
    data = parse_test_infra_file(test_infra_file)
    assert data == []


@pytest.fixture
def test_infra_data(mocker):
    data = [('foo', 'bar'), ('baz', None)]
    mocker.patch('src.web.test_infra.parse_test_infra_file', return_value=data)
    mocker.patch('config.DIR_ASSETS', 'assets', create=True)
    mocker.patch('config.URL_WIKIPEDIA', 'wiki')
    return data


def test_load_test_infra_data(test_infra_data):
    """Check that data is formed as expected."""
    items = load_test_infra_data()
    assert len(items) == len(test_infra_data)
    assert items[0]['article_name'] == 'foo'
    assert items[0]['check'] == 'bar'
    assert items[1]['article_name'] == 'baz'
    assert items[1]['check'] is None
