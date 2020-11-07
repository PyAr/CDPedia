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

import os
from urllib.parse import unquote

NULL = "_"

QUOTER = {c: '%{:02X}'.format(ord(c)) for c in './%'}


class Namespaces:
    """A list of namespaces initiated from different sources."""

    _fname = 'namespace_prefixes.txt'

    def __init__(self):
        self._namespaces = None

    def load(self, dirbase):
        """Load the info from the file in the specified directory."""
        path = os.path.join(dirbase, self._fname)
        with open(path, 'rt', encoding='utf8') as fh:
            self._namespaces = {x.strip() for x in fh}

    def dump(self, prefixes, dirbase):
        """Dump the given information to file in the specified directory."""
        path = os.path.join(dirbase, self._fname)
        with open(path, 'wt', encoding="utf-8") as fh:
            for prefix in sorted(prefixes):
                fh.write(prefix + "\n")

    def __contains__(self, tocheck):
        if self._namespaces is None:
            raise RuntimeError("Namespaces not initiated.")

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
    return unquote(filename)


to_filename = _quote


def get_path_file(page):
    """Get a path (3 dirs) and file name from the page."""
    if not page:
        raise ValueError

    # quote here once (the ":" is untouched, and split below will work ok, as namespaces don't
    # contain quoted chars)
    page = full_page = _quote(page)

    if ':' in page:
        namespace, maybe_page = page.split(':', 1)
        if namespace in namespaces:
            page = maybe_page

    dirs = []
    if len(page) == 1:
        dirs = [page, NULL, NULL]
    elif len(page) == 2:
        dirs = [page[0], page[1], NULL]
    else:
        dirs = list(page[:3])

    return ('/'.join(dirs), full_page)


def from_path(path):
    """ Quita los 3 dirs del path """
    path = to_pagina(path)
    return path[6:]
