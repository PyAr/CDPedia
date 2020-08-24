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
print('time with pil:', (timeit.timeit('resize_image(True)', setup='from __main__ import resize_image', number=10)))
print(len(os.listdir(dst)), "images")
shutil.rmtree(dst)
print('time with convert:', (timeit.timeit('resize_image(False)', setup='from __main__ import resize_image', number=10)))
print(len(os.listdir(dst)), "images")

