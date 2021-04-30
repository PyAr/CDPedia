# Copyright 2021 CDPedistas (see AUTHORS.txt)
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

import os
import shutil

from src.images.download import optimize_png

import pytest


@pytest.fixture
def image_config(tmp_path):
    img_test_name = 'tests/fixtures/image_to_optimize.png'
    test_path = str(tmp_path / 'image_to_optimize.png')
    shutil.copy(img_test_name, test_path)
    init_size = os.stat(img_test_name).st_size
    return test_path, init_size


def test_optimize(image_config):
    img_path, init_size = image_config
    optimize_png(img_path, init_size, init_size)
    final_size = os.stat(img_path).st_size
    assert init_size > final_size
