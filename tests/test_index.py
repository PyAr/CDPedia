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
import logging
from pprint import pprint as pp
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
    assert items == [(0, "ala blanca", 3)]


def test_several_items(create_index):
    """Several items stored."""
    idx = create_index([(["ala", "blanca"], "ala blanca", 3),
                        (["conejo", "blanco"], "conejo blanco", 5),
                        ])
    items = sorted(idx.items())
    assert items == [(0, "ala blanca", 3), (1, "conejo blanco", 5)]
    tokens = sorted(idx.keys())
    assert tokens == ["ala", "blanca", "blanco", "conejo"]


def test_search(create_index):
    """Several items stored."""
    idx = create_index([(["ala", "blanca"], "ala blanca", 3),
                        (["conejo", "blanco"], "conejo blanco", 5),
                        ])
    res = searchidx(idx, ["ala"])
    assert res == [("ala blanca", 3)]


def test_several_results(caplog, create_index):
    """Several results for one key stored."""
    caplog.set_level(logging.INFO)
    idx = create_index([(["ala", "blanca"], "ala blanca", 3),
                        (["conejo", "blanco"], "conejo blanco", 5),
                        (["conejo", "negro"], "conejo negro", 6),
                        ])
    # items = [a for a in idx.search(["conejo"])]
    res = searchidx(idx, ["conejo"])
    assert res == [("conejo negro", 6), ("conejo blanco", 5)]

def test_several_keys(caplog, create_index):
    """Several item stored."""
    caplog.set_level(logging.INFO)
    idx = create_index([(["ala", "blanca"], "ala blanca", 3),
                        (["conejo", "blanco"], "conejo blanco", 5),
                        (["conejo", "negro"], "conejo negro", 6),
                        ])
    # items = [a for a in idx.search(["conejo"])]
    res = searchidx(idx, ["conejo", "negro"])
    assert res == [("conejo negro", 6)]

def test_word_scores(caplog, create_index):
    """Test the order in the results."""
    pg_scores = 9000
    caplog.set_level(logging.INFO)
    titles = ["coneja blanca", "gradaciones entre los colores de blanca", "blanca"]
    info = [(t.split(), t, pg_scores) for t in titles]
    idx = create_index(info)
    res = searchidx(idx, ["blanca"])
    expected = zip(["blanca", "coneja blanca", "gradaciones entre los colores de blanca"], [pg_scores] * 3)
    expected = [(title, score) for title, score in expected]
    assert res == expected

def test_many_results(caplog, create_index):
    """Test with many pages of results."""
    pg_scores = 9000
    caplog.set_level(logging.INFO)
    titles = """blanca ojeda
        coneja blanca
        gradaciones entre los colores de blanca
        conejo blanca
        caja blanca
        limpieza de blanca
        blanca casa
        es blanca la paloma
        Blanca gómez
        recuerdos de blanca
        blanca"""
    titles = [s.strip() for s in titles.split("\n")]
    info = [(t.lower().split(), t, pg_scores) for t in titles]
    idx = create_index(info)
    res = searchidx(idx, ["blanca"], debug=False)
    assert len(res) == len(titles)

def searchidx(idx, keys, debug=False):
    if debug:
        data = list(idx._search_asoc_docs(keys))
        data = list(data)
        pp(data)
        founded = idx._search_merge_results(data)
        founded = list(founded)
        pp(founded)
        ordered = idx._search_order_items(founded)
        ordered = list(ordered)
        pp(ordered)
        res = [idx.get_doc(ndoc) for _, ndoc in ordered]
    else:
        res = [a for a in idx.search(keys)]
    return res

'''
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
