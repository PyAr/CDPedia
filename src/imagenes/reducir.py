# -*- coding: utf8 -*-

from __future__ import with_statement, division

import codecs
import config
import Image
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

def scaleImage(frompath, topath, scale_factor):
    """
    Reduces the size ofan image by the scale_factor using the PIL library
    """
    scale_ratio = scale_factor / 100 # since scale_factor is in percentage
    try:
        im = Image.open(frompath)
    except IOError:
        logger.warning("Couldn't read image at %s" % frompath)
        return -1
    
    # pull out the original dimensions and calculate resized dimensions
    width, height = im.size 
    resize_tuple  = (int(width * scale_ratio), int(height * scale_ratio))
    
    # resize and save at new destination
    output_image = im.resize(resize_tuple)
    output_image.save(topath)
    logger.info("Success! Resized image saved at %s" % topath)
    
    return 0


def run(verbose):
    notfound = 0
    done_ahora = {}

    # leemos las imágenes que procesamos antes
    done_antes = {}
    if os.path.exists(config.LOG_REDUCDONE):
        with codecs.open(config.LOG_REDUCDONE, "r", "utf-8") as fh:
            for linea in fh:
                partes = linea.strip().split()
                escala = int(partes[0])
                dskurl = partes[1]
                done_antes[dskurl] = escala

    src = os.path.join(config.DIR_TEMP, "images")
    dst = os.path.join(config.DIR_IMGSLISTAS)

    # cargamos la escala que va para cada página
    with codecs.open(config.LOG_REDUCCION, "r", "utf-8") as fh:
        for linea in fh:
            partes = linea.strip().split(config.SEPARADOR_COLUMNAS)
            escl = int(partes[0])
            dskurl = partes[1]

            frompath = os.path.join(src, dskurl)
            topath = os.path.join(dst, dskurl)
            if not os.path.exists(frompath):
                logger.warning("Don't have the img %r", frompath)
                notfound += 1
                continue

            # create the dir to hold it
            dirname = os.path.dirname(topath)
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            # reglas para no escalar algunas imagenes: math/*, .png, y < 2KB
            if dskurl.startswith('math') or dskurl.endswith('.png') or \
               os.stat(frompath).st_size < 2048:
#                print "Forzando imagen a escala 100 por reglas", repr(dskurl)
                escl = 100

            # vemos si lo que hay que hacer ahora no lo teníamos hecho de antes
            escl_antes = done_antes.get(dskurl)
            if escl_antes == escl:
                done_ahora[dskurl] = escl
                continue

            # cambiamos el tamaño si debemos, sino sólo copiamos
            if verbose:
                print "Reescalando a %d%% la imagen %s" % (escl, dskurl.encode("utf8"))
            if escl == 100:
                done_ahora[dskurl] = 100
                shutil.copyfile(frompath, topath)
            else:
                # scale image using PIL
                status = scaleImage(frompath=frompath, topath=topath, scale_factor=escl)
                
                if not status:
                    done_ahora[dskurl] = escl

    # guardamos lo que procesamos ahora
    with codecs.open(config.LOG_REDUCDONE, "w", "utf-8") as fh:
        for dskurl, escl in done_ahora.iteritems():
            fh.write("%3d %s\n" % (escl, dskurl))

    # vemos lo que sobró de la vez pasada y lo borramos
    for dskurl in (set(done_antes) - set(done_ahora)):
        fullpath = os.path.join(dst, dskurl)
        try:
            os.remove(fullpath)
        except OSError as exc:
            logger.error("When erasing %r (got OSError %s)", fullpath, exc)

    # si es verbose ya avisamos una por una
    if not verbose and notfound:
        print "  WARNING: No encontramos %d imágenes!" % (notfound,)
    return notfound
