# -*- coding: utf-8 -*-

# Copyright 2010-2017 CDPedistas (see AUTHORS.txt)
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
# For further info, check  http://code.google.com/p/cdpedia/

"""Functions to transform names into filesystem useful strings.

Basically, deal with "/" and "." that are forbidden characters in the filesystem.

Current implementation complies with two needs:

- that a filename converted from a page can be converted back to the page name

- that the 3-dirs path can be deduced from a filename (after conversion from a page)
"""

from __future__ import unicode_literals

import codecs
import os
import urllib

import config

NULL = "_"

QUOTER = {c: '%{:02X}'.format(ord(c)) for c in './%'}


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


def _quote(string):
    """Similar to urllib.quote, but only working with problematic filesystem chars.

    IOW, will replace only "." and "/" for it's encoded values (and "%", for unambiguity).
    """
    return ''.join(QUOTER.get(c, c) for c in string)


def to_pagina(filename):
    """Unquote.

    s == to_pagina(to_filename(s))
    """
    return urllib.unquote(filename)


to_filename = _quote


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

    pagina = _quote(pagina)
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
