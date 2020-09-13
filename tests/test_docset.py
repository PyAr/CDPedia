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


import pytest

from src.armado import sqlite_index


def test_delta_encode_decode():
    """Test encoding and decoding something."""
    values = [1, 4, 7, 12, 34, 56, 72, 76, 80, 83]
    docset = sqlite_index.DocSet()
    encoded = docset.delta_encode(values)
    assert values == docset.delta_decode(encoded)

# --- Test the DocSet class


def test_repr_docset():
    """Test creating a DocSet."""
    docset = sqlite_index.DocSet()
    data = {123: 12, 234: 1, 56: 5, 432: 9}
    for k, v in data.items():
        docset.append(k, v)
    descript = str(docset)
    assert descript.index("len=") == len('<Docset: ')
    data = dict(list((k, k + 5) for k in range(1, 150)))
    docset2 = sqlite_index.DocSet()
    for k, v in data.items():
        docset2.append(k, v)
        docset2.append(k, v + 1)
    descript = str(docset2)
    assert descript.endswith("...>")
    assert len(descript.split(":")) - len(descript.split("|")) <= 2


def test_create_doc_set():
    """Test creating a DocSet."""
    docset = sqlite_index.DocSet()
    data = {123: 12, 234: 1, 56: 5, 432: 9}
    for k, v in data.items():
        docset.append(k, v)
    assert len(data) == len(docset)


def test_invalid_docset():
    """Test creating an invalid DocSet."""
    docset = sqlite_index.DocSet()
    data = {0: 0xFF, 123: 12, 234: 1, 56: 5, 432: 9}
    for k, v in data.items():
        docset.append(k, v)
    with pytest.raises(ValueError) as _:
        docset.encode()


def test_encode_decode_docset():
    """Test encode & decode a DocSet."""
    docset = sqlite_index.DocSet()
    data = {123: 12, 234: 1, 56: 5, 432: 9}
    for k, v in data.items():
        docset.append(k, v)
        docset.append(k, v * 2)
    encoded = docset.encode()
    docset2 = sqlite_index.DocSet.decode(encoded)
    assert docset == docset2


def test_empty_docsets():
    """Test encode & decode an empty DocSet."""
    docset = sqlite_index.DocSet()
    encoded = docset.encode()
    docset2 = sqlite_index.DocSet.decode(encoded)
    assert docset == docset2
    assert len(docset) == 0

# ----- Test the sqlite database using DocSet type


def test_database():
    """Test database."""
    con = sqlite_index.open_connection(":memory:")
    sql = "CREATE TABLE DocSets (docset BLOB);"
    con.executescript(sql)
    docset = sqlite_index.DocSet()
    data = {123: 12, 234: 1, 56: 5, 432: 9}
    for k, v in data.items():
        docset.append(k, v)
    encoded = docset.encode()
    sql = "INSERT INTO DocSets (docset) VALUES (?);"
    con.execute(sql, [encoded, ])
    con.commit()
    sql = "SELECT docset FROM DocSets LIMIT 1"
    cur = con.cursor()
    cur.execute(sql)
    res = [row[0] for row in cur.fetchall()]
    assert len(res) == 1
    docset2 = sqlite_index.DocSet.decode(res[0])
    assert docset == docset2

# ----- Test convert title to filename


@pytest.mark.parametrize('title, filename', (
    ("one tiny special title", r"O/n/e/One_tiny_special_title"),
    ("ab", 'A/b/_/Ab'),
    ("ac\\dc", 'A/c/\\/Ac\\dc'),
    ("ñ}ùẃŷ⅝¡⅛°ḧ", 'Ñ/}/ù/Ñ}ùẃŷ⅝¡⅛°ḧ'),
))
def test_to_filename(title, filename):
    """Test to filename."""
    assert filename == sqlite_index.to_filename(title)


def test_to_empty_title():
    """Test to filename w/empty title error."""
    with pytest.raises(ValueError):
        sqlite_index.to_filename('')
