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


import shutil
import tempfile

import pytest

from src.armado import sqlite_index


# --- Test the DocSet class

def test_delta_encode_decode():
    """Test encoding and decoding something."""
    values = [1, 4, 7, 12, 34, 56, 72, 76, 80, 83]
    dc = sqlite_index.DocSet()
    encoded = dc.delta_encode(values)
    assert values == dc.delta_decode(encoded)

def test_create_doc_set():
    """Test creating a DocSet."""
    dc = sqlite_index.DocSet()
    data = {123:12, 234:1, 56:5, 432: 9}
    for k, v in data.items():
        dc.append(k, v)
    assert len(data) == len(dc)

def test_encode_decode_docset():
    """Test encode & decode a DocSet."""
    dc = sqlite_index.DocSet()
    data = {123:12, 234:1, 56:5, 432: 9}
    for k, v in data.items():
        dc.append(k, v)
    encoded = dc.encode()
    dc2 = sqlite_index.DocSet(encoded=encoded)
    assert dc == dc2

def test_empty_docsets():
    """Test encode & decode an empty DocSet."""
    dc = sqlite_index.DocSet()
    encoded = dc.encode()
    dc2 = sqlite_index.DocSet(encoded=encoded)
    assert dc == dc2
    assert len(dc) == 0

# ----- Test the sqlite database using DocSet type

def test_database():
    """Test database."""
    con = sqlite_index.open_connection(":memory:")
    sql = "CREATE TABLE DocSets (docset BLOB);"
    con.executescript(sql)
    dc = sqlite_index.DocSet()
    data = {123:12, 234:1, 56:5, 432: 9}
    for k, v in data.items():
        dc.append(k, v)
    encoded = dc.encode()
    sql = "INSERT INTO DocSets (docset) VALUES (?);"
    con.execute(sql, [encoded,])
    con.commit()
    sql = "SELECT docset FROM DocSets LIMIT 1"
    cur = con.cursor()
    cur.execute(sql)
    res = [row[0] for row in cur.fetchall()]
    assert len(res) == 1
    dc2 = sqlite_index.DocSet(encoded=res[0])

 # ----- Test convert title to filename

def test_to_filename():
    """Test to filename."""
    title = "one tiny special title"
    filename = sqlite_index.to_filename(title)
    assert filename == r"O/n/e/One_tiny_special_title"
