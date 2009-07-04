# -*- coding: utf8 -*-

import os
import shutil
import config
import subprocess
import codecs


class Reduce(object):
    _scales = [
        (1000**2, 200),
        (500**2,  120),
        (250**2,   80),
        (100**2,   50),
    ]

    def __init__(self):
        self.src = os.path.join(config.DIR_TEMP, "images")
        self.dst = os.path.join(config.DIR_ASSETS, "images")
        self.lensrc = len(self.src)

    def proc(self, arch):
        frompath = os.path.join(self.src, arch)
        if not os.path.exists(frompath):
            print u"WARNING: no tenemos la imágen", frompath
            return

        topath = os.path.join(self.dst, arch)
        if os.path.exists(topath):
            return

        # create the dir to hold it
        dirname = os.path.dirname(topath)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        try:
            w, h = self.get_size(frompath)
            goto_size = self.get_rescaled_size(w, h)
        except Exception, e:
            print "Oops, error %s in file: %s" % (e, frompath)
            goto_size = None

        # cambiamos el tamaño si debemos, sino sólo copiamos
        if goto_size is None:
            shutil.copyfile(frompath, topath)
        else:
            self.do_resize(frompath, topath, goto_size)

    def get_rescaled_size(self, old_w, old_h):
        for maxboth, goto in self._scales:
            if old_w * old_h >= maxboth:
                return goto

    def get_size(self, path):
        cmd = ['identify', '-format', '%W %H|', path]

        # execute it
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                                    stderr=subprocess.STDOUT)
        t = p.stdout.read()
        p.stdout.close()

        # cuando es en capas vienen muchos pares de valores, tomamos el primero
        prim = t.split("|")[0]
        w, h = map(int, prim.split())
        return w, h

    def do_resize(self, input, output, size):
        cmd = ['convert', input, '-resize', '{s}x{s}'.format(s=size), output]
        subprocess.call(cmd)


def run(verbose):
    # por ahora no achicamos nada, va todo igualito...

    red = Reduce()

    for linea in codecs.open(config.LOG_IMAGENES, "r", "utf8"):
        arch, _ = linea.strip().split(config.SEPARADOR_COLUMNAS)
        red.proc(arch)
