# Copyright 2008-2020 CDPedistas (see AUTHORS.txt)
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

"""Calculate which images will be included in final release and their scaling values."""


import logging
import operator
import os

import config
from src.preprocessing import preprocess


logger = logging.getLogger("images.calculate")

SCALES = (100, 75, 50)


class Scaler:
    """Compute values for image scaling."""

    def __init__(self, total_items):
        # prepare the limits generator.
        self.scale_vals = []
        reduction = config.imageconf['image_reduction'][:-1]
        # total images in percentage to incorporate
        add_images = sum(reduction)
        # number of images of the required percentage to process
        # more elements can be added and dimensions changed in subsequent processes
        self.total_items = 0
        for (percentage, scale) in zip(reduction, SCALES):
            quantity = total_items * percentage // 100
            self.scale_vals.append((quantity, scale))
            self.total_items += quantity
        vals_tplt = ' - '.join('{} at {}%'.format(quant, scale)
                               for quant, scale in self.scale_vals)
        logger.info("Add images: %i%% - %i total | Scales: %s",
                    add_images, self.total_items, vals_tplt)

    def get_items(self):
        limit = 0
        for quant, scale in self.scale_vals:
            for _ in range(quant):
                yield (limit, scale)
                limit += 1


def image_is_required(url):
    """Decide if an image should be mandatorily included."""
    # always include svg images (mostly equations, highly compressible)
    _, ext = os.path.splitext(url)
    return ext.lower() == '.svg'


def run():
    """Calculate the sizes of the images."""
    # load relation: articles -> images
    page_images = {}
    dynamics = []
    separator = config.SEPARADOR_COLUMNAS
    with open(config.LOG_IMAGPROC, "rt", encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split(separator)
            dir3 = parts[0]
            fname = parts[1]
            dskurls = parts[2:]
            if dir3 == config.DYNAMIC:
                dynamics.extend(dskurls)
            else:
                page_images[dir3, fname] = dskurls

    # images that must be included in final release
    images_required = set()
    required_enabled = config.IMAGES_REQUIRED

    # sort images by the highest priority of the pages in which they are included,
    # this way images from more important articles will get a better scaling value.
    images_optional = {}
    preprocessed = preprocess.pages_selector.top_pages
    for file_position, (dir3, fname, _) in enumerate(preprocessed):
        # get the images that correspond to this file
        dskurls = page_images[(dir3, fname)]

        for url in dskurls:
            if required_enabled and image_is_required(url):
                images_required.add(url)
            # if it's an optional image, save position (priority) of the article it belongs
            elif url not in images_optional:
                images_optional[url] = file_position

    # assign highest priority to dynamic images
    for url in dynamics:
        images_optional[url] = -1

    # load image list to map disk paths to web addresses
    dskweb = {}
    with open(config.LOG_IMAGENES, "rt", encoding="utf-8") as fh:
        for line in fh:
            dsk, web = line.strip().split(separator)
            dskweb[dsk] = web

    # all images saved to LOG_REDUCTION will be downloaded and scaled
    log_reduction = open(config.LOG_REDUCCION, 'wt', encoding='utf8')

    # save info of required images (won't be scaled)
    for dskurl in images_required:
        weburl = dskweb[dskurl]
        info = '100', dskurl, weburl
        log_reduction.write(separator.join(info) + '\n')

    # sort optional images by assigned priority
    images_optional = sorted(images_optional.items(), key=operator.itemgetter(1))
    scaler = Scaler(len(images_optional))
    for idx, scale in scaler.get_items():
        dskurl, _ = images_optional[idx]
        weburl = dskweb[dskurl]
        info = (str(scale), dskurl, weburl)
        log_reduction.write(separator.join(info) + "\n")

    log_reduction.close()
    selected_req = len(images_required)
    logger.info("Images to add: %i required, %i in total including scalables",
                selected_req, (selected_req + scaler.total_items))
