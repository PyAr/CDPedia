# -*- coding: utf8 -*-

# Copyright 2014-2020 CDPedistas (see AUTHORS.txt)
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


@pytest.fixture(params=[sqlite_index.Index])
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


@pytest.fixture(params=[sqlite_index.Index])
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
    idx = create_index([])
    items = list(idx.items())
    assert items == []

def test_one_item(create_index):
    """Only one item."""
    idx = create_index([(["ala", "blanca"], "ala blanca", 3)])
    items = list(idx.items())
    assert items == [(1, "ala blanca", 3)]

def test_several_items(create_index):
    """Several items stored."""
    idx = create_index([(["ala", "blanca"], "ala blanca", 3),
                        (["conejo", "blanco"], "conejo blanco", 5),
                        ])
    items = sorted(idx.items())
    assert items == [(1, "ala blanca", 3), (2, "conejo blanco", 5)]
    tokens = sorted(idx.keys())
    assert tokens == ["ala", "blanca", "blanco", "conejo"]

def test_search(create_index):
    """Several items stored."""
    idx = create_index([(["ala", "blanca"], "ala blanca", 3),
                        (["conejo", "blanco"], "conejo blanco", 5),
                        ])
    items = list([a for a in idx.search(["ala"])])
    assert items == [[("ala blanca", 3)]]

'''
def test_same_keys(create_index):
    """Two items with the same key."""
    idx = create_index([("a", 3), ("a", 5)])
    items = list(idx.items())
    (item,) = items
    k, v = item
    assert k == "a" and sorted(v) == [3, 5]


def test_mixed(create_index):
    """Two items with the same key and something else."""
    idx = create_index([("a", 3), (u"ñ", 7), ("a", 5)])
    items = sorted(idx.items())
    assert items == [("a", [3, 5]), (u"ñ", [7])]


# --- Test the .values method.

def test_values_nothing(create_index):
    """Nothing in the index."""
    idx = create_index([])
    values = list(idx.values())
    assert values == []


def test_values_one_item(create_index):
    """Only one item."""
    idx = create_index([("a", 3)])
    values = sorted(idx.values())
    assert values == [3]


def test_values_several_values(create_index):
    """Several values stored."""
    idx = create_index([("a", 3), ("b", 5)])
    values = sorted(idx.values())
    assert values == [3, 5]


def test_values_same_keys(create_index):
    """Two values with the same key."""
    idx = create_index([("a", 3), ("a", 5)])
    values = sorted(idx.values())
    assert values == [3, 5]


def test_values_mixed(create_index):
    """Two values with the same key and something else."""
    idx = create_index([(u"ñ", 3), ("b", 7), (u"ñ", 5)])
    values = sorted(idx.values())
    assert values == [3, 5, 7]


# --- Test the .random method.

def test_random_one_item(create_index):
    """Only one item."""
    idx = create_index([("a", 3)])
    value = idx.random()
    assert value == 3


def test_random_several_values(create_index):
    """Several values stored."""
    idx = create_index([("a", 3), ("b", 5)])
    value = idx.random()
    assert value in (3, 5)


# --- Test the "in" functionality.

def test_infunc_nothing(create_index):
    """Nothing in the index."""
    idx = create_index([])
    assert "a" not in idx


def test_infunc_one_item(create_index):
    """Only one item."""
    idx = create_index([("a", 3)])
    assert "a" in idx
    assert "b" not in idx


def test_infunc_several_values(create_index):
    """Several values stored."""
    idx = create_index([("a", 3), (u"ñ", 5)])
    assert "a" in idx
    assert u"ñ" in idx
    assert "c" not in idx


# --- Test the .search method.

def test_search_nothing(create_index):
    """Nothing in the index."""
    idx = create_index([])
    res = idx.search(["a"])
    assert list(res) == []


def test_search_one_item(create_index):
    """Only one item."""
    idx = create_index([("a", 3)])
    res = idx.search(["a"])
    assert list(res) == [3]
    res = idx.search(["b"])
    assert list(res) == []


def test_search_several_values(create_index):
    """Several values stored."""
    idx = create_index([("a", 3), ("b", 5)])
    res = idx.search(["a"])
    assert list(res) == [3]
    res = idx.search(["b"])
    assert list(res) == [5]
    res = idx.search(["c"])
    assert list(res) == []


def test_search_same_keys(create_index):
    """Two values with the same key."""
    idx = create_index([("a", 3), ("a", 5)])
    res = idx.search(["a"])
    assert set(res) == {3, 5}
    res = idx.search(["b"])
    assert list(res) == []


def test_search_mixed(create_index):
    """Two values with the same key and something else."""
    idx = create_index([("a", 3), (u"ñ", 7), ("a", 5)])
    res = idx.search(["a"])
    assert set(res) == {3, 5}
    res = idx.search([u"ñ"])
    assert list(res) == [7]
    res = idx.search(["c"])
    assert list(res) == []


def test_search_nopartial(create_index):
    """Does not find partial values."""
    idx = create_index([("aa", 3)])
    res = idx.search(["a"])
    assert list(res) == []


def test_search_and(create_index):
    """Check that AND is applied."""
    idx = create_index([("a", 3), ("b", 3), ("a", 5), ("c", 5)])
    res = idx.search(["a", "b"])
    assert list(res) == [3]
    res = idx.search(["b", "c"])
    assert list(res) == []


# --- Test the .partial_search method.

def test_partialsearch_nothing(create_index):
    """Nothing in the index."""
    idx = create_index([])
    res = idx.partial_search(["a"])
    assert list(res) == []


def test_partialsearch_prefix(create_index):
    """Match its prefix."""
    idx = create_index([(u"abñc", 3)])
    res = idx.partial_search(["ab"])
    assert list(res) == [3]
    res = idx.partial_search(["ad"])
    assert list(res) == []


def test_partialsearch_suffix(create_index):
    """Match its suffix."""
    idx = create_index([(u"abñd", 3)])
    res = idx.partial_search([u"ñd"])
    assert list(res) == [3]
    res = idx.partial_search(["ad"])
    assert list(res) == []


def test_partialsearch_middle(create_index):
    """Match in the middle."""
    idx = create_index([(u"abñd", 3)])
    res = idx.partial_search([u"bñ"])
    assert list(res) == [3]
    res = idx.partial_search(["cb"])
    assert list(res) == []


def test_partialsearch_exact(create_index):
    """Exact match."""
    idx = create_index([("abcd", 3)])
    res = idx.partial_search(["abcd"])
    assert list(res) == [3]


def test_partialsearch_several_values(create_index):
    """Several values stored."""
    idx = create_index([("aa", 3), ("bc", 5), ("dbj", 7), ("ab", 9)])
    res = idx.partial_search(["a"])
    assert set(res) == {3, 9}
    res = idx.partial_search(["b"])
    assert set(res) == {5, 7, 9}
    res = idx.partial_search(["c"])
    assert list(res) == [5]
    res = idx.partial_search(["d"])
    assert list(res) == [7]


def test_partialsearch_and(create_index):
    """Check that AND is applied."""
    idx = create_index([("oao", 3), ("bll", 3), ("nga", 5), ("xxc", 5), ("ooa", 7)])
    res = idx.partial_search(["a", "b"])
    assert list(res) == [3]
    res = idx.partial_search(["b", "c"])
    assert list(res) == []
    res = idx.partial_search(["a", "o"])
    assert set(res) == {3, 7}


# --- Test the .create method in the non-working cases.

def test_create_non_iterable(get_engine):
    """It must iterate on what receives."""
    tempdir, engine = get_engine()
    with pytest.raises(TypeError):
        engine.create(tempdir, None)


def test_create_key_string(get_engine):
    """Keys can be string."""
    tempdir, engine = get_engine()
    engine.create(tempdir, [("aa", 33)])


def test_create_key_unicode(get_engine):
    """Keys can be unicode."""
    tempdir, engine = get_engine()
    engine.create(tempdir, [(u"año", 33)])


def test_create_key_badtype(get_engine):
    """Keys must be strings or unicode."""
    tempdir, engine = get_engine()
    with pytest.raises(TypeError):
        engine.create(tempdir, [(1, 3)])


def test_create_return_quantity(get_engine):
    """Must return the quantity indexed."""
    tempdir, engine = get_engine()
    q = engine.create(tempdir, [])
    assert q == 0
    q = engine.create(tempdir, [("a", 1)])
    assert q == 1
    q = engine.create(tempdir, [("a", 1), ("b", 2)])
    assert q == 2
    q = engine.create(tempdir, [("a", 1), ("a", 2)])
    assert q == 2
'''
