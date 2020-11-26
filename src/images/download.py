# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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

"""Download images."""

import logging
import os
import subprocess
import urllib.request
import urllib.error
import time

from PIL import Image

import config

from src import utiles


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
        'Ubuntu/8.10 (intrepid) Firefox/3.0.5')
}

logger = logging.getLogger("images.download")


class FetchingError(Exception):
    """Error while fetching an image."""
    def __init__(self, msg, *msg_args):
        super().__init__(msg)
        self.msg_args = msg_args


def remove_metadata(img):
    """Open and Close image to remove metadata with pillow."""
    if not img.lower().endswith('.svg'):
        size = os.stat(img).st_size
        img_pil = Image.open(img)
        img_pil.save(img)
        final_size = os.stat(img).st_size
        logger.debug("Removing Metadata from: %r", img)
        logger.debug("Metadata Removed: %r(bytes)", size - final_size)


def optimize_png(img):
    """Run pngquant to optimize PNG format."""
    if img.lower().endswith('.png'):
        size = os.stat(img).st_size
        subprocess.run(["pngquant", "-f", "--ext", ".png", "--quality=40-70", img])
        final_size = os.stat(img).st_size
        logger.debug("PNG optimized: %r", img)
        logger.debug("Weight Removed: %r(bytes)", size - final_size)


def _download(url, fullpath):
    """Download image from url and save it to disk."""
    basedir, _ = os.path.split(fullpath)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    req = urllib.request.Request(url, headers=HEADERS)
    u = urllib.request.urlopen(req)

    img = u.read()
    with open(fullpath, "wb") as fh:
        fh.write(img)

    remove_metadata(fullpath)
    optimize_png(fullpath)


def download(data):
    """Download image from url, retry on error."""
    url, fullpath = data

    # seconds to sleep before each retrial (starting from the end)
    retries = [5, 1, .3]

    while True:
        try:
            _download(url, fullpath)
            # download OK
            return
        except Exception as err:
            if isinstance(err, urllib.error.HTTPError) and err.code == 404:
                raise FetchingError("Failed with HTTPError 404 on url %r", url)
            if not retries:
                raise FetchingError("Giving up retries after %r on url %r", err, url)
            time.sleep(retries.pop())


def retrieve():
    """Download the images from the net."""
    download_list = []

    # load images that couldn't be downloaded previously
    log_errors = os.path.join(config.DIR_TEMP, "images_neterror.txt")
    if os.path.exists(log_errors):
        with open(log_errors, "rt", encoding="utf8") as fh:
            imgs_problems = set(x.strip() for x in fh)
    else:
        imgs_problems = set()

    for line in open(config.LOG_REDUCCION, "rt", encoding="utf8"):
        line = line.strip()
        if not line:
            continue

        _, arch, url = line.split(config.SEPARADOR_COLUMNAS)
        fullpath = os.path.join(config.DIR_TEMP, "images", arch)

        if url not in imgs_problems and not os.path.exists(fullpath):
            download_list.append((url, fullpath))

    utiles.pooled_exec(download, download_list, pool_size=5, known_errors=[FetchingError])
