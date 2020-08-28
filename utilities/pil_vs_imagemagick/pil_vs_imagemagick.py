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

import subprocess
import os
import shutil
import timeit
from PIL import Image

scale = 50
dst = os.path.join("pil_vs_imagemagick", "resized-images")
dump = 'pil_vs_imagemagick/dump'


def with_pil(frompath, topath):
    img = Image.open(frompath)
    new_size = [int(s * scale / 100) for s in img.size]
    img_resized = img.resize(new_size)
    img_resized.save(topath)


def with_convert(frompath, topath, scale):
    cmd = ['convert', frompath, '-resize', '%d%%' % (scale,), topath]
    subprocess.call(cmd)


def resize_image(pil):
    for base, dirs, images in os.walk(dump):
        for image in images:
            frompath = os.path.join(base, image)
            topath = os.path.join(dst, image)
            dirname = os.path.dirname(topath)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # rules to skip scaling of some images: .svg, .png, and < 2KB
            imgsize = os.stat(frompath).st_size
            if frompath.endswith('.svg') or frompath.endswith('.png') or imgsize < 2048:
                pass
            else:
                if pil:
                    with_pil(frompath, topath)
                else:
                    with_convert(frompath, topath, scale)


if os.path.exists(dst):
    shutil.rmtree(dst)
print('time with pil:', (timeit.timeit(
    'resize_image(True)',
    setup='from __main__ import resize_image',
    number=10)))
print(len(os.listdir(dst)), "images")
shutil.rmtree(dst)
print('time with convert:', (timeit.timeit(
    'resize_image(False)',
    setup='from __main__ import resize_image',
    number=10)))
print(len(os.listdir(dst)), "images")
