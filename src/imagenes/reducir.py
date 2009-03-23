# -*- coding: utf8 -*-

import os
import shutil
import config

def run(verbose):
    # por ahora no achicamos nada, va todo igualito...

    src = os.path.join(config.DIR_TEMP, "images")
    dst = os.path.join(config.DIR_ASSETS, "images")

    if os.path.exists(dst):
        print "Borramos las imágenes reducidas anteriores"
        shutil.rmtree(dst)

    if os.path.exists(src):
        print "Llevando imgs de %s a %s" % (src, dst)
        shutil.copytree(src, dst)
