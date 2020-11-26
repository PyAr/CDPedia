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

"""Tests for the 'scale' module."""

import unittest
import os

from PIL import Image
from src.images.scale import scale_image


class ScaleImagesTestCase(unittest.TestCase):
    """Tests for Scale."""

    def setUp(self):
        super().setUp()
        self.original = os.path.join(os.getcwd(), 'tests', 'fixtures', 'image-to-scale.jpg')
        self.scaled = os.path.join(os.getcwd(), 'tests', 'fixtures', 'scaled-image.jpg')

    def test_scale(self):
        scale_image(self.original, self.scaled, 50)
        img = Image.open(self.scaled)
        resized_size = img.size
        self.assertEqual(resized_size, (25, 25))

    def tearDown(self):
        os.remove(self.scaled)
