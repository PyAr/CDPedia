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

import os

import config
from src.images import calculate

import pytest


@pytest.fixture
def image_config(mocker, tmp_path):
    """Dummy configuration for image processing."""
    mocker.patch('config.LOG_IMAGPROC', str(tmp_path / 'proc.txt'))
    mocker.patch('config.LOG_IMAGENES', str(tmp_path / 'imag.txt'))
    mocker.patch('config.LOG_REDUCCION', str(tmp_path / 'red.txt'))
    mocker.patch('config.LOG_IMAGES_EMBEDDED', str(tmp_path / 'emb.txt'))
    imgr = {'image_reduction': [5, 5, 10, 80]}
    mocker.patch('config.imageconf', imgr, create=True)


@pytest.fixture
def image_data(mocker, image_config):
    """Dummy data expected for image processing."""

    # images in articles: dir3|article_title|img1|img2...
    with open(config.LOG_IMAGPROC, 'wt', encoding='utf-8') as fh:
        fh.write('e/g/g|eggs|foo.png|bar.bmp\n')
        fh.write('b/a/c|bacon|foo.png\n')
        fh.write('h/a/m|ham|baz.svg\n')
        fh.write('s/p/a|spam|spam.svg\n')
        fh.write('__dynamic__|portals|bar.bmp\n')  # special

    # diskname and external URL of images: name|url
    with open(config.LOG_IMAGENES, 'wt', encoding='utf-8') as fh:
        fh.write('foo.png|url_foo\n')
        fh.write('bar.bmp|url_bar\n')
        fh.write('baz.svg|url_baz\n')
        fh.write('spam.svg|url_spam\n')

    # Mock top pages selection: (dir3, fname, score)
    tops = [
        ('e/g/g', 'eggs', 80),
        ('b/a/c', 'bacon', 60),
        ('h/a/m', 'ham', 40),
        ('s/p/a', 'spam', 20)
    ]
    mocker.patch('src.images.calculate.preprocess.pages_selector',
                 mocker.Mock(top_pages=tops))


def test_scaler(image_config):
    """Test correct reduction values for a given number of images."""
    images = 100  # keep it simple
    s = calculate.SCALES
    p = config.imageconf['image_reduction']
    expect = [x for i in range(len(s)) for x in [s[i]] * p[i]]
    scaler = calculate.Scaler(images)
    result = [scaler(i) for i in range(images)]
    assert expect == result


@pytest.mark.parametrize('image_url, expected_result', (
    ('foo/bar.svg', True),
    ('foo/bar..SVg', True),
    ('foo/bar.png', False),
    ('foo/bar.svg.png', False),
    ('spam.gif', False),
    ('foo/svg', False),
))
def test_is_not_required(image_url, expected_result):
    """Test images that should/shouldn't be recognized as required."""
    assert expected_result == calculate.image_is_required(image_url)


@pytest.mark.parametrize('reduction', (
    (0, 0, 0, 100),
    (10, 20, 30, 50),
    (20, 30, 50, 0),
    (100, 0, 0, 0),
))
def test_required_images(reduction, mocker, image_data):
    """Test that required images are included independently of reduction values."""
    mocker.patch('config.IMAGES_REQUIRED', True)
    mocker.patch('config.imageconf', {'image_reduction': reduction})
    calculate.run()
    with open(config.LOG_REDUCCION, 'r', encoding='utf-8') as fh:
        images = fh.read()
    assert 'baz.svg' in images
    assert 'spam.svg' in images


def test_required_images_only(mocker, image_data):
    """Test inclusion of required images only."""
    mocker.patch('config.IMAGES_REQUIRED', True)
    reduction = [0, 0, 0, 100]  # no optional images
    mocker.patch('config.imageconf', {'image_reduction': reduction})
    calculate.run()
    with open(config.LOG_REDUCCION, 'r', encoding='utf-8') as fh:
        images = fh.read()
    assert 'baz.svg' in images
    assert 'spam.svg' in images
    # only the two required SVG images should be included
    assert len(images.split()) == 2


def test_no_images(mocker, image_data):
    """Test no images included."""
    mocker.patch('config.IMAGES_REQUIRED', False)
    mocker.patch('config.imageconf', {'image_reduction': [0, 0, 0, 100]})
    calculate.run()
    assert os.path.getsize(config.LOG_REDUCCION) == 0


def test_no_repeated_images(mocker, image_data):
    """Image with same name should be included only once."""
    mocker.patch('config.IMAGES_REQUIRED', True)
    mocker.patch('config.imageconf', {'image_reduction': [30, 30, 40, 0]})
    calculate.run()
    with open(config.LOG_REDUCCION, 'rt', encoding='utf-8') as fh:
        images = fh.read()
    assert images.count('foo.png') == 1


def test_dynamic_images_priority(mocker, image_data):
    """Dynamic images should be first in images list."""
    mocker.patch('config.IMAGES_REQUIRED', False)
    mocker.patch('config.imageconf', {'image_reduction': [30, 30, 40, 0]})
    calculate.run()
    with open(config.LOG_REDUCCION, 'rt', encoding='utf-8') as fh:
        first_image_info = fh.read().split()[0]
    assert 'bar.bmp' in first_image_info
