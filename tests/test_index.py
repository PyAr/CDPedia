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

from src.armado import easy_index
from src.armado import compressed_index
from src.armado import sqlite_index


def decomp(data):
    """To write docset in a compact way.

    Ej: 'my title/2;second title/4'
    """
    docs = [n.strip().split("/") for n in data.split(";")]
    docs = [(n[0], int(n[1])) for n in docs]
    return docs


def abrev(result):
    """Cut auto generated html title in 0 position."""
    result = list(result)
    if not result:
        return result
    return [tuple(r[1:3]) for r in result]


class DataSet:
    """Creates data lists to put in the index."""
    fixtures = {}

    @classmethod
    def add_fixture(cls, key, data):
        docs = decomp(data)
        info = [(n[0].lower().split(" "), n[1], ('', n[0])) for n in docs]
        cls.fixtures[key] = info

    def __init__(self, key):
        self.name = key
        self.info = []
        if key in self.fixtures:
            self.info = self.fixtures[key]

    def __eq__(self, other):
        return self.info == other

    def __repr__(self):
        return "Fixture %s: %r" % (self.name, self.info)


def test_auxiliary():
    DataSet.add_fixture("one", "ala blanca/3")
    assert DataSet("one") == [(['ala', 'blanca'], 3, ('', 'ala blanca'))]
    r = [["A/l/a/Ala_Blanca", "ala blanca", 3],
         ["A/l/a/Ala", "ala", 8]]
    s = "ala blanca/3; ala/8"
    assert abrev(r) == decomp(s)


DataSet.add_fixture("A", "ala blanca/3")
DataSet.add_fixture("B", "ala blanca/3; conejo blanco/5; conejo negro/6")
data = """\
        aaa/4;
        abc/4;
        bcd/4;
        abd/4;
        bbd/4
    """
DataSet.add_fixture("E", data)


@pytest.fixture(params=[compressed_index.Index, easy_index.Index, sqlite_index.Index])
def create_index(request):
    """Create an index with given info in a temp dir, load it and return built index."""
    tempdir = tempfile.mkdtemp()

    def f(info):
        # Create the index with the parametrized engine
        engine = request.param
        engine.create(tempdir, info)

        # Load the index and give it to use
        index = engine(tempdir)
        return index

    try:
        yield f
    finally:
        shutil.rmtree(tempdir)


@pytest.fixture(params=[compressed_index.Index, easy_index.Index, sqlite_index.Index])
def get_engine(request):
    """Provide temp dirs and index engines to the tests."""
    tempdir = tempfile.mkdtemp()
    engine = request.param
    try:
        yield lambda: (tempdir, engine)
    finally:
        shutil.rmtree(tempdir)


# --- Test the .items method.


def test_items_nothing(create_index):
    """Nothing in the index."""
    with pytest.raises(ValueError) as _:
        create_index([])


def test_one_item(create_index):
    """Only one item."""
    idx = create_index(DataSet("A").info)
    values = idx.values()
    assert abrev(values) == decomp("ala blanca/3")


def test_several_items(create_index):
    """Several items stored."""
    idx = create_index(DataSet("B").info)
    values = sorted(idx.values())
    assert abrev(values) == decomp("ala blanca/3; conejo blanco/5; conejo negro/6")
    tokens = sorted([str(k) for k in idx.keys()])
    assert tokens == ["ala", "blanca", "blanco", "conejo", "negro"]

# --- Test the .random method.


def test_random_one_item(create_index):
    """Only one item."""
    idx = create_index(DataSet("A").info)
    value = idx.random()
    assert abrev([value]) == decomp("ala blanca/3")


def test_random_several_values(create_index):
    """Several values stored."""
    idx = create_index(DataSet("B").info)
    value = abrev([idx.random()])
    assert value[0] in decomp("ala blanca/3; conejo blanco/5; conejo negro/6")

# --- Test the "in" functionality.


def test_infunc_one_item(create_index):
    """Only one item."""
    idx = create_index(DataSet("B").info)
    assert "ala" in idx
    assert "bote" not in idx
