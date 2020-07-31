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

"""Embed pre-selected images in HTML source."""

import logging
import os

import bs4

import config

logger = logging.getLogger('images.embed')


def image_is_embeddable(imgpath, imgsize):
    """Decide if given image will be embedded in HTML source."""
    _, ext = os.path.splitext(imgpath)
    return ext.lower() == '.svg' and imgsize < 40960


class _EmbedImages:
    """Embed images in HTML file."""

    def embed_images(self, htmlpath, images):
        """Embed specified images in HTML source."""

        # load html soup
        with open(htmlpath, 'rb') as fh:
            soup = bs4.BeautifulSoup(fh, features='lxml', from_encoding='utf-8')

        # search img tags to embed images
        for node in soup.find_all('img', src=True):
            # discard query part from URL (and all that follows)
            src = node.attrs['src'].split('?', 1)[0]
            if src not in images:
                continue

            # take embeddable images from original download location
            imgpath = config.DIR_TEMP + src  # src starts with `/`
            kind = os.path.splitext(src)[1].lstrip('.').lower()
            if kind == 'svg':
                self.embed_vector(node, imgpath)
            else:
                logger.error('Embed method not found for: %r', src)

        # dump updated html
        html = soup.encode(encoding='utf-8')
        # keep only body content
        soup.html.unwrap()
        soup.body.unwrap()
        with open(htmlpath, 'wb') as fh:
            fh.write(html)

    def load_vector(self, imgpath):
        """Read SVG from disk and return a Tag object."""
        with open(imgpath, 'rb') as fh:
            xml = bs4.BeautifulSoup(fh, features='xml', from_encoding='utf-8')
        return xml.find('svg')

    def embed_vector(self, node, imgpath):
        """Embed SVG image directly in HTML tree."""
        svg = self.load_vector(imgpath)
        node.replace_with(svg)


def _load_embed_data():
    """Load `page -> images_to_embed` relation."""
    # load to-be-embedded image paths
    with open(config.LOG_IMAGES_EMBEDDED, 'rt', encoding='utf-8') as fh:
        images_to_embed = set(line.strip() for line in fh)

    # find what images must be embedded in each page
    page_embeds = {}
    prefix = config.IMAGES_URL_PREFIX
    separator = config.SEPARADOR_COLUMNAS
    with open(config.LOG_IMAGPROC, "rt", encoding="utf-8") as fh:
        for line in fh:
            dir3, fname, *page_images = line.strip().split(separator)
            if dir3 == config.DYNAMIC:
                continue
            embeds = images_to_embed & set(page_images)
            if embeds:
                page_embeds[(dir3, fname)] = set(prefix + e for e in embeds)
    return page_embeds


def run():
    """Embed pre-selected images into HTML sources."""
    embedder = _EmbedImages()
    page_embeds = _load_embed_data()
    for (dir3, fname), images in page_embeds.items():
        htmlpath = os.path.join(config.DIR_PAGSLISTAS, dir3, fname)
        logger.debug('Embedding %3d images in %s', len(images), fname)
        embedder.embed_images(htmlpath, images)
