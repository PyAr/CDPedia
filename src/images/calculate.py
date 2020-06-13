# -*- coding: utf8 -*-

# Copyright 2008-2015 CDPedistas (see AUTHORS.txt)
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

"""Calculate image scaling values."""

from __future__ import with_statement, division, unicode_literals

import codecs
import logging
import operator

import config
from src.preprocessing import preprocess


logger = logging.getLogger("images.calculate")

SCALES = (100, 75, 50, 0)


class Scaler(object):
    """Compute values for image scaling."""

    def __init__(self, total_items):
        # prepare limits
        vals = []
        base = 0
        reduction = config.imageconf['image_reduction']
        logger.info("Reduction: %s", reduction)
        for (percentage, scale) in zip(reduction, SCALES):
            quantity = total_items * percentage / 100
            vals.append((quantity + base, scale))
            base += quantity
        logger.info("Scales: %s", vals)

        self.limit = 0
        self.gen_pairs = (x for x in vals)

    def __call__(self, num):
        if num >= self.limit:
            # continue with next values
            (self.limit, self.scale) = next(self.gen_pairs)
        return self.scale


def run():
    """Calculate the sizes of the images."""
    # load relation: articles -> images
    page_images = {}
    dynamics = []
    with codecs.open(config.LOG_IMAGPROC, "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split(config.SEPARADOR_COLUMNAS)
            dir3 = parts[0]
            fname = parts[1]
            dskurls = parts[2:]
            if dir3 == config.DYNAMIC:
                dynamics.extend(dskurls)
            else:
                page_images[dir3, fname] = dskurls

    # sort images by the highest priority of the pages in which they are included,
    # this way images from more important articles will get a better scaling value.
    images = {}
    preprocessed = preprocess.pages_selector.top_pages
    for posic_archivo, (dir3, fname, _) in enumerate(preprocessed):
        # get images i this file
        dskurls = page_images[(dir3, fname)]

        # for each new image, save position of the file (article priority)
        for url in dskurls:
            if url not in images:
                images[url] = posic_archivo

    # incorporate the dynamic images at the very top
    for url in dynamics:
        images[url] = -1

    total_images = len(images)
    images = sorted(images.iteritems(), key=operator.itemgetter(1))

    # load image list to map disk paths to web addresses
    dskweb = {}
    with codecs.open(config.LOG_IMAGENES, "r", encoding="utf-8") as fh:
        for linea in fh:
            dsk, web = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dskweb[dsk] = web

    logger.info("Calculating scales for %d images", total_images)
    scaler = Scaler(total_images)
    log_reduccion = codecs.open(config.LOG_REDUCCION, "w", encoding="utf8")
    for i, (dskurl, _) in enumerate(images):
        scale = scaler(i)
        if scale == 0:
            # done, no more images
            log_reduccion.close()
            return

        weburl = dskweb[dskurl]
        info = (str(int(scale)), dskurl, weburl)
        log_reduccion.write(config.SEPARADOR_COLUMNAS.join(info) + "\n")
