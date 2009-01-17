# -*- coding: utf8 -*-

'''Algunas pequeñas funciones útiles.'''

import config

import re

# Coincide si se empieza con uno de los namespaces más ~
RE_NAMESPACES = re.compile(r'(%s)~(.*)' % '|'.join(config.NAMESPACES))

def separaNombre(nombre):
    '''Devuelve (namespace, resto) de un nombre de archivo del wiki.'''
    m = RE_NAMESPACES.match(nombre)
    if not m:
        result = (None, nombre)
    else:
        result = m.groups()
    return result
