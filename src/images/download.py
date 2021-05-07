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

# seconds to sleep before each retrial when downloading (starting from the end)
RETRIES = [5, 1, .3]

# Turning off the PIL debug logs as are too noisy.
logging.getLogger("PIL").setLevel(logging.INFO)

logger = logging.getLogger("images.download")


class FetchingError(Exception):
    """Error while fetching an image."""
    def __init__(self, msg, *msg_args):
        super().__init__(msg)
        self.msg_args = msg_args


def optimize_image(img_path):
    """Open and Close image to remove metadata with pillow."""
    size = os.stat(img_path).st_size
    with Image.open(img_path) as img:
        img.save(img_path)
    final_size = os.stat(img_path).st_size
    if img_path.lower().endswith('.png'):
        optimize_png(img_path, size, final_size)
    else:
        logger.debug("Metadata removed from %r: %d(bytes) removed",
                     img_path, size - final_size)


def optimize_png(img_path, original_size, current_size):
    """Run pngquant to optimize PNG format."""
    temp_fpath = img_path + ".temp"
    subprocess.run(["pngquant", "--quality=40-70", "--output={}".format(temp_fpath), img_path])
    os.rename(temp_fpath, img_path)
    final_size = os.stat(img_path).st_size
    logger.debug("Metadata removed from %r: %d(bytes) removed"
                 " · PNG, Extra clean-up: %d(bytes) removed",
                 img_path, original_size - current_size, current_size - final_size)


def _download(url, fullpath):
    """Download image from url and save it to disk."""
    req = urllib.request.Request(url, headers=HEADERS)
    u = urllib.request.urlopen(req)

    img = u.read()
    with open(fullpath, "wb") as fh:
        fh.write(img)


def download(data):
    """Download image from url, retry on error."""
    url, fullpath = data
    retries = RETRIES.copy()

    basedir, _ = os.path.split(fullpath)
    # call it directly with exist_ok=True; it's better than verify if it exists
    # and then create, as if it's done in two lines a race condition may happen
    # (this function internally just catches the error)
    os.makedirs(basedir, exist_ok=True)

    while True:
        try:
            _download(url, fullpath)
        except Exception as err:
            if isinstance(err, urllib.error.HTTPError) and err.code == 404:
                raise FetchingError("Failed with HTTPError 404 on url %r", url)
            if not retries:
                raise FetchingError("Giving up retries after %r on url %r", err, url)
            time.sleep(retries.pop())
        else:
            # download OK
            break

    # run optimize_image if images are not .svg or .gif
    if not fullpath.lower().endswith(('.svg', '.gif')):
        optimize_image(fullpath)


def retrieve(images_dump_dir):
    """Download the images from the net."""
    download_list = []
    previous_count = 0
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
        fullpath = os.path.join(images_dump_dir, arch)

        if os.path.exists(fullpath):
            previous_count += 1

        elif url not in imgs_problems:
            download_list.append((url, fullpath))

    utiles.pooled_exec(download, previous_count, download_list,
                       pool_size=5, known_errors=[FetchingError])
