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

import bs4

import config
from src.images import embed

import pytest


@pytest.fixture
def svg_image(tmp_path):
    """Dummy SVG image."""
    svg = '<?xml version="1.0" encoding="UTF-8"?>\n<svg><rect/></svg>'
    filedir = tmp_path / config.IMAGES_URL_PREFIX.lstrip(r'/')
    filedir.mkdir(parents=True)
    filepath = filedir / 'foo.svg'
    with filepath.open('wt', encoding='utf-8') as fh:
        fh.write(svg)
    return str(filepath)


@pytest.fixture
def html_file(tmp_path):
    """Dummy HTML file with images."""
    html = '<html><body><img src="/images/foo.svg?s=10-10"></body></html>'
    # x = tmp_path.mkdir('f/o/o', parents=True)
    filedir = tmp_path / 'f/o/o'
    filedir.mkdir(parents=True)
    filepath = filedir / 'foo'  # no extension
    with filepath.open('wt', encoding='utf-8') as fh:
        fh.write(html)
    return str(filepath)


@pytest.fixture
def images_data(mocker, tmp_path):
    """Dummy image data files."""
    mocker.patch('config.DIR_TEMP', str(tmp_path))
    mocker.patch('config.DIR_PAGSLISTAS', str(tmp_path))

    # page images
    mocker.patch('config.LOG_IMAGPROC', str(tmp_path / 'img.txt'))
    sep = config.SEPARADOR_COLUMNAS
    with open(config.LOG_IMAGPROC, 'wt', encoding='utf-8') as fh:
        fh.write(sep.join(('f/o/o', 'foo', 'foo.png', 'foo.svg')))

    # images to be embedded
    mocker.patch('config.LOG_IMAGES_EMBEDDED', str(tmp_path / 'emb.txt'))
    with open(config.LOG_IMAGES_EMBEDDED, 'wt', encoding='utf-8') as fh:
        fh.write('foo.svg')


@pytest.mark.parametrize('imgpath, imgsize, expected_result', (
    ('foo/bar.svg', 20480, True),
    ('foo/bar.SvG', 30720, True),
    ('foo/bar.svg', 51200, False),
    ('foo/bar.png', 20480, False),
    ('foo/bar.gif', 20480, False),
    ('foo/bar.svg.png', 20480, False),
))
def test_is_embeddable(imgpath, imgsize, expected_result):
    """Test that embeddable images are recognized correctly."""
    assert expected_result == embed.image_is_embeddable(imgpath, imgsize)


def test_load_embed_data(images_data):
    """Test images to embed data loading."""
    data = embed._load_embed_data()
    expected_key = 'f/o/o', 'foo'
    expected_val = {'/images/foo.svg'}
    assert data.get(expected_key) == expected_val


def test_load_vector(svg_image):
    """Test correct loading of SVG images."""
    embedder = embed._EmbedImages()
    node = embedder.load_vector(svg_image)
    assert getattr(node, 'name', None) == 'svg'


def test_embed_vector(svg_image):
    """Test embedding of SVG image."""
    embedder = embed._EmbedImages()
    soup = bs4.BeautifulSoup('<img src="foo.svg">', features='lxml')
    assert soup.svg is None
    embedder.embed_vector(soup.img, svg_image)
    assert soup.svg is not None


def test_embed_images(html_file, mocker):
    """Test general method for embedding images."""
    mocker.patch('src.images.embed._EmbedImages.embed_vector', mocker.Mock())
    embedder = embed._EmbedImages()
    image = '/images/foo.svg'
    embedder.embed_images(html_file, {image})
    args = embedder.embed_vector.call_args[0]
    assert len(args) == 2
    assert args[1] == config.DIR_TEMP + image


def test_run(svg_image, html_file, images_data):
    with open(html_file, 'rb') as fh:
        html = bs4.BeautifulSoup(fh, features='lxml', from_encoding='utf-8')
    assert html.find('img') is not None
    assert html.find('svg') is None
    embed.run()
    with open(html_file, 'rb') as fh:
        html = bs4.BeautifulSoup(fh, features='lxml', from_encoding='utf-8')
    assert html.find('img') is None
    assert html.find('svg') is not None
