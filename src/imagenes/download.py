# -*- coding: utf8 -*-

import codecs

import config

def traer(verbose):
    for linea in codecs.open(config.LOG_IMAGENES, "r", "utf8"):
        arch, url = linea.split()
        arch = "../../../../images/" + arch
        url = "http://upload.wikimedia.org/wikipedia" + url
        print "bajando", repr(arch), repr(url)
