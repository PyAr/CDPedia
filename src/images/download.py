# -*- coding: utf8 -*-

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

import collections
import logging
import os
import urllib.request
import urllib.error

import config

from src import distributor, utiles


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
        'Ubuntu/8.10 (intrepid) Firefox/3.0.5')
}

logger = logging.getLogger("images.download")


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


def download(data):
    """Download image from url, retry on error."""
    url, fullpath = data
    retries = 3
    for i in range(retries):
        try:
            _download(url, fullpath)
            # download OK
            return None
        except urllib.error.HTTPError as err:
            # dense error, return code
            return "HTTPError: %d" % (err.code,)
        except Exception as err:
            # weird error, retry
            logger.debug("Error downloading image, retrying: %s", err)
            # if enough retries, return last error
            if i == retries - 1:
                return str(err)


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

    tot = len(download_list)
    p = distributor.Pool(download, 5)
    tl = utiles.TimingLogger(30, logger.debug)
    errors = collections.Counter()
    n_ok = 0
    n_err = 0
    for i, result in enumerate(p.process(download_list), 1):
        (url, fullpath), stt = result
        if stt is None:
            n_ok += 1
        else:
            errors[stt] += 1
            n_err += 1
            with open(log_errors, "at", encoding="utf8") as fh:
                fh.write(url + "\n")

        tl.log("Downloaded image %d/%d (ok=%d, err=%d)", i, tot, n_ok, n_err)

    for code, quant in errors.most_common():
        logger.warning("Had errors: code=%r quant=%d", code, quant)
