# -*- coding: utf-8 -*-

import codecs
import os

import config

NULL = u"_"
BARRA = u"SLASH"


class Namespaces(object):
    """A dynamic loading list of namespaces."""
    def __init__(self, path=None):
        self._namespaces = None
        if path is None:
            self.filepath = os.path.join(config.DIR_ASSETS, 'dynamic', "namespace_prefixes.txt")
        else:
            self.filepath = path

    def __contains__(self, tocheck):
        if self._namespaces is None:
            with codecs.open(self.filepath, 'rt', encoding='utf8') as fh:
                self._namespaces = set(x.strip() for x in fh)

        return tocheck in self._namespaces

namespaces = Namespaces()


def _escape_dir(s):
    return s.replace(u"/", BARRA).replace(u".", NULL)


def _escape_filename(s):
    return s.replace(u"/", BARRA)


def to_pagina(filename):
    """
    s == to_pagina(_escape_filename(s))
    """
    return filename.replace(BARRA, u"/")


def to_path(pagina):
    """
    Pagina tiene que ser unicode.
    """
    if not pagina:
        raise ValueError

    if ':' in pagina:
        namespace, posible_pagina = pagina.split(':', 1)
        if namespace in namespaces:
            pagina = posible_pagina

    pagina = _escape_dir(pagina)
    dirs = []
    if len(pagina) == 1:
        dirs = [pagina, NULL, NULL]
    elif len(pagina) == 2:
        dirs = [pagina[0], pagina[1], NULL]
    else:
        dirs = list(pagina[:3])

    return '/'.join(dirs)


def from_path(path):
    """ Quita los 3 dirs del path """
    path = to_pagina(path)
    return path[6:]


to_filename = _escape_filename
