# -*- coding: utf8 -*-

import os
import shutil
import config
import subprocess
import codecs


def run(verbose):
    notfound = 0

    # cargamos la escala que va para cada página
    pag_escala = {}
    with codecs.open(config.LOG_REDUCCION, "r", "utf-8") as fh:
        for linea in fh:
            partes = linea.strip().split()
            puntos = int(partes[0])
            dir3 = partes[1]
            fname = partes[2]
            pag_escala[dir3, fname] = puntos

    # sacamos las fotos de cada página, y tomamos la mayor escala que le toca
    escala_imag = {}
    with codecs.open(config.LOG_IMAGPROC, "r", "utf-8") as fh:
        for linea in fh:
            partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
            dir3 = partes[0]
            fname = partes[1]
            bogus = int(partes[2])
            if bogus:
                continue
            dskurls = partes[3:]

            # vemos que escala le corresponde a este archivo, si no está es
            # que era cero y no entra!
            escala = pag_escala[dir3, fname]

            # si estaba, vemos el máximo
            for url in dskurls:
                escala_imag[url] = max(escala_imag.get(url, 0), escala)

    src = os.path.join(config.DIR_TEMP, "images")
    dst = os.path.join(config.DIR_ASSETS, "images")

    # reducimos las imágenes
    for arch, escl in escala_imag.iteritems():
        frompath = os.path.join(src, arch)
        topath = os.path.join(dst, arch)
        if not os.path.exists(frompath):
            if verbose:
                print "WARNING: no tenemos la img", repr(frompath)
            notfound += 1
            continue

        # create the dir to hold it
        dirname = os.path.dirname(topath)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # cambiamos el tamaño si debemos, sino sólo copiamos
        if verbose:
            print "Rescaling a {0}% la imágen {1}".format(escl, arch.encode("utf8"))
        if escl == 100:
            shutil.copyfile(frompath, topath)
        else:
            cmd = ['convert', frompath, '-resize', '{0}%'.format(escl), topath]
            subprocess.call(cmd)

    # si es verbose ya avisamos una por una
    if not verbose and notfound:
        print "  WARNING: No encontramos {0} imágenes!".format(notfound)
    return notfound
