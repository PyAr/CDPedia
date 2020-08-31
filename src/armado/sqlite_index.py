# Copyright 2020 CDPedistas (see AUTHORS.txt)
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
# For further info, check  https://github.com/PyAr/CDPedia/


import array
import os
import sqlite3
from collections import defaultdict

from src.armado import to3dirs

PAGE_SIZE = 512


class DocSet:
    """Data type to encode, decode & compute documents-id's sets."""
    def __init__(self):
        self._docs_list = defaultdict(list)

    def append(self, docid, position):
        """Append an item to the docs_list."""
        self._docs_list[docid].append(position)

    def __len__(self):
        return len(self._docs_list)

    def __repr__(self):
        value = repr(self._docs_list).replace("[", "").replace("],", "|").replace("]})", "}")
        curly = value.index("{")
        value = value[curly:curly + 75]
        if not value.endswith("}"):
            value += " ..."
        return "<Docset: len={} {}>".format(len(self._docs_list), value)

    def __eq__(self, other):
        return self._docs_list == other._docs_list

    @staticmethod
    def delta_encode(ordered):
        """Compress an array of numbers into a bytes object."""
        result = array.array('B')
        add_to_result = result.append

        prev_doc = 0
        for doc in ordered:
            doc, prev_doc = doc - prev_doc, doc
            while True:
                b = doc & 0x7F
                doc >>= 7
                if doc:
                    # the number is not exhausted yet,
                    # store these 7b with the flag and continue
                    add_to_result(b | 0x80)
                else:
                    # we're done, store the remaining bits
                    add_to_result(b)
                    break

        return result.tobytes()

    @staticmethod
    def delta_decode(ordered):
        """Decode a compressed encoded bucket.

        - ordered is a bytes object, representing a byte's array
        - ctor is the final container
        - append is the callable attribute used to add an element into the ctor
        """
        result = []
        add_to_result = result.append

        prev_doc = doc = shift = 0

        for b in ordered:
            doc |= (b & 0x7F) << shift
            shift += 7

            if not (b & 0x80):
                # the sequence ended
                prev_doc += doc
                add_to_result(prev_doc)
                doc = shift = 0

        return result

    def encode(self):
        """Encode to store compressed inside the database."""
        if not self._docs_list:
            return ""
        docs_list = []
        for key, values in self._docs_list.items():
            docs_list.extend((key, value) for value in values)
        docs_list.sort()
        docs = [v[0] for v in docs_list]
        docs_enc = DocSet.delta_encode(docs)
        # if any score is greater than 255 or lesser than 1, it won't work
        position = [v[1] for v in docs_list]
        if not all(position):
            raise ValueError("Positions can't be zero.")
        position = array.array("B", position)
        return position.tobytes() + b"\x00" + docs_enc

    @classmethod
    def decode(cls, encoded):
        """Decode a compressed docset."""
        docset = cls()
        docset._docs_list = {}
        if len(encoded) > 1:
            limit = encoded.index(b"\x00")
            docsid = cls.delta_decode(encoded[limit + 1:])
            positions = array.array('B')
            positions.frombytes(encoded[:limit])
            docset._docs_list = defaultdict(list)
            for docid, position in zip(docsid, positions):
                docset._docs_list[docid].append(position)
        return docset


def open_connection(filename):
    """Connect and register data types and aggregate function."""
    # Register the adapter
    def adapt_docset(docset):
        return docset.encode()
    sqlite3.register_adapter(DocSet, adapt_docset)

    # Register the converter
    def convert_docset(s):
        return DocSet.decode(s)
    sqlite3.register_converter("docset", convert_docset)

    con = sqlite3.connect(filename, check_same_thread=False, detect_types=sqlite3.PARSE_COLNAMES)
    return con


def to_filename(title):
    """Compute the filename from the title."""
    if len(title) == 0:
        raise ValueError("Title must have at least one character")
    tt = title.replace(" ", "_")
    if len(tt) >= 2:
        tt = tt[0].upper() + tt[1:]
    elif len(tt) == 1:
        tt = tt[0].upper()

    dir3, arch = to3dirs.get_path_file(tt)
    expected = os.path.join(dir3, arch)
    return expected
