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
from src.armado.cdpindex import tokenize
from src.armado.sqlite_index import IndexEntry


def get_ie(title):
    """Creates an index_entry object with default values."""
    return IndexEntry(rtype=IndexEntry.TYPE_ORIG_ARTICLE,
                      title=title.strip(),
                      link=title.strip(),
                      score=0)


def to_idx_data(titles):
    """Generate a list of data prepared for create index."""
    return [[tokenize(ttl), 0, get_ie(ttl), set()] for ttl in titles]


@pytest.fixture()
def create_index(tmpdir):
    """Create an index with given info in a temp dir, load it and return built index."""

    def f(info):
        # Create the index with the parametrized engine
        sqlite_index.Index.create(str(tmpdir), info)

        # Load the index and give it to use
        index = sqlite_index.Index(str(tmpdir))
        return index

    yield f


# --- Test the .items method.


def test_items_nothing(create_index):
    """Nothing in the index."""
    with pytest.raises(ValueError) as _:
        create_index([])


def test_one_item(create_index):
    """Only one item."""
    idx = create_index(to_idx_data(["ala blanca"]))
    values = idx.values()
    # assert DataSet("A") == values
    assert list(values) == [get_ie("ala blanca")]


def test_several_items(create_index):
    """Several items stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    values = idx.values()
    assert set(values) == {get_ie('ala blanca'), get_ie('conejo blanco'), get_ie('conejo negro')}
    assert set(idx.keys()) == {"ala", "blanca", "blanco", "conejo", "negro"}


# --- Test the .random method.


def test_random_one_item(create_index):
    """Only one item."""
    idx = create_index(to_idx_data(["ala blanca"]))
    value = idx.random()
    assert value == get_ie("ala blanca")


def test_random_several_values(create_index):
    """Several values stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    value = list([idx.random()])[0]
    assert value in {get_ie('ala blanca'), get_ie('conejo blanco'), get_ie('conejo negro')}

# --- Test the "in" functionality.


def test_infunc_one_item(create_index):
    """Only one item."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    assert "ala" in idx
    assert "bote" not in idx

# --- Test the .search method.


def test_search_failed(create_index):
    """Several items stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    res = list(idx.search(["botero"]))
    assert res == []


def test_search_unicode(create_index):
    """Several items stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    res1 = list(idx.search(["Alá"]))
    res2 = list(idx.search(["ála"]))
    assert res1 == res2


def test_search(create_index):
    """Several items stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    res = list(idx.search(["ala"]))
    assert res == [get_ie("ala blanca")]


def test_several_results(create_index):
    """Several results for one key stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    # items = [a for a in idx.search(["conejo"])]
    res = idx.search(["conejo"])
    assert set(res) == {get_ie('conejo blanco'), get_ie('conejo negro')}


def test_several_keys(create_index):
    """Several item stored."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    # items = [a for a in idx.search(["conejo"])]
    res = idx.search(["conejo", "negro"])
    assert set(res) == {get_ie('conejo negro')}


def test_many_results(create_index):
    """Test with many pages of results."""
    data = """\
        blanca ojeda;
        coneja blanca;
        gradaciones entre los colores de blanca;
        conejo blanca;
        caja blanca;
        limpieza de blanca;
        blanca casa;
        es blanca la paloma;
        Blanca gómez;
        recuerdos de blanca;
        blanca
    """.split(';')
    idx = create_index(to_idx_data(data))
    assert len(data) == len([v for v in idx.values()])
    res = list(idx.search(["blanca"]))
    assert len(res) == len(data)


def test_search_prefix(create_index):
    """Match its prefix."""
    idx = create_index(to_idx_data(["ala blanca", "conejo blanco", "conejo negro"]))
    res = idx.search(["blanc"])
    assert set(res) == {get_ie('ala blanca'), get_ie('conejo blanco')}
    res = idx.search(["zz"])
    assert list(res) == []


def test_search_several_values(create_index):
    """Several values stored."""
    data = ["aaa", "abc", "bcd", "abd", "bbd"]
    idx = create_index(to_idx_data(data))
    res = idx.search(["a"])
    assert set(res) == {get_ie("aaa"), get_ie("abc"), get_ie("abd")}
    res = idx.search(["b"])
    assert set(res) == {get_ie("abc"), get_ie("abd"), get_ie("bcd"), get_ie("bbd")}
    res = idx.search(["c"])
    assert set(res) == {get_ie("abc"), get_ie("bcd")}
    res = idx.search(["d"])
    assert set(res) == {get_ie("bcd"), get_ie("abd"), get_ie("bbd")}
    res = idx.search(["o"])
    assert set(res) == set()


def test_search_and(create_index):
    """Check that AND is applied."""
    data = ["aaa", "abc", "bcd", "abd", "bbd"]
    idx = create_index(to_idx_data(data))
    res = idx.search(["a", "b"])
    assert set(res) == {get_ie("abc"), get_ie("abd")}
    res = idx.search(["b", "c"])
    assert set(res) == {get_ie("abc"), get_ie("bcd")}
    res = idx.search(["a", "o"])
    assert set(res) == set()

# --- Test the .search method.


def test_redir(create_index):
    data = to_idx_data(["aaa", "abc", "bcd", "abd", "bbd"])
    data[0][-1] = {("zzz", "xxx")}
    data[1][-1] = {("111",), ("000",)}
    idx = create_index(data)
    res = idx.search(["z"])
    idx_entry = get_ie("aaa")
    idx_entry.rtype = IndexEntry.TYPE_REDIRECT
    idx_entry.subtitle = "zzz xxx"
    assert set(res) == {idx_entry}
