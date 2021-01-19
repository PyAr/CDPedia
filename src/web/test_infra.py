# Copyright 2011-2020 CDPedistas (see AUTHORS.txt)
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

import configparser
import os

import config
from src.armado import to3dirs
from .utils import get_orig_link

TEST_INFRA_FILENAME = 'test_infra.txt'


def parse_test_infra_file(filepath):
    """Parse test infra file for getting titles and issues to check.

    Example file:

        [es]
        Portal:Portada # Check page looks OK
        República_Agentina # Article with 'Argentina' title is shown
        Satélites_de_Saturno

        [fr]
        Château # Image galleries shouldn't overflow

    """
    parser = configparser.ConfigParser(
        allow_no_value=True,
        delimiters=('#',),
        interpolation=None,
    )
    parser.optionxform = str  # don't alter key names
    with open(filepath, 'r', encoding='utf-8') as fh:
        parser.read_file(fh)
    return parser.items(config.LANGUAGE)


def load_test_infra_data():
    """Load data from TEST_INFRA_FILENAME."""
    _path = os.path.join(config.DIR_ASSETS, 'dynamic', TEST_INFRA_FILENAME)
    items = parse_test_infra_file(_path)
    total = len(items)
    data = []
    for number, (name, check) in enumerate(items, start=1):
        orig_link = get_orig_link(name)
        article_name = to3dirs.to_filename(name)
        item = {
            'article_name_unquoted': name,
            'article_name': article_name,
            'orig_link': orig_link,
            'number': number,
            'check': check,
            'total': total,
        }
        data.append(item)
    return data
