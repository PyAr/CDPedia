# -*- coding: utf8 -*-

# Copyright 2011-2020 CDPedistas (see AUTHORS.txt)
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

import threading
import time
import unittest
import uuid

from src.web.searcher import Searcher, Cache


class FakeIndex(object):
    """A fake index."""

    def __init__(self):
        self.ready = threading.Event()
        self.fake_full = []
        self.fake_partial = []

    def search(self, _):
        """Fake full search."""
        self.ready.wait()
        for item in self.fake_full:
            yield item

    def partial_search(self, _):
        """Fake partial search."""
        self.ready.wait()
        for item in self.fake_partial:
            yield item


class SearcherTestCase(unittest.TestCase):
    """Tests for the Searcher."""

    def setUp(self):
        """Set up."""
        self.index = FakeIndex()
        self.searcher = Searcher(self.index, 3)

    def tearDown(self):
        """Tear down."""
        self.index.ready.set()

    def test_startsearch_ready(self):
        """Return the uuid if ready."""
        self.index.ready.set()
        search_id = self.searcher.start_search(['words'])
        uuid.UUID(search_id)
        real_search, results, _, _ = self.searcher.active_searches[search_id]
        self.assertTrue(isinstance(real_search, threading.Thread))
        self.assertFalse(results)

    def test_startsearch_notready(self):
        """Return the id even if not ready."""
        assert not self.index.ready.is_set()
        search_id = self.searcher.start_search(['words'])
        uuid.UUID(search_id)
        real_search, results, _, _ = self.searcher.active_searches[search_id]
        self.assertTrue(isinstance(real_search, threading.Thread))
        self.assertFalse(results)

    def test_startsearch_samesearch_cached(self):
        """Same search returns same id."""
        self.index.ready.set()
        search_id_1 = self.searcher.start_search(['words'])
        assert search_id_1 in self.searcher.active_searches
        search_id_2 = self.searcher.start_search(['words'])
        search_id_3 = self.searcher.start_search(['other'])
        self.assertEqual(search_id_1, search_id_2)
        self.assertNotEqual(search_id_1, search_id_3)

    def test_startsearch_samesearch_notcached(self):
        """Same search returns other id if search was lost."""
        self.index.ready.set()
        search_id_1 = self.searcher.start_search(['words'])
        del self.searcher.active_searches[search_id_1]
        search_id_2 = self.searcher.start_search(['words'])
        self.assertNotEqual(search_id_1, search_id_2)

    def test_cache_size(self):
        """How the cache works."""
        srch1 = self.searcher.start_search(['1'])
        self.assertTrue(srch1 in self.searcher.active_searches)
        srch2 = self.searcher.start_search(['2'])
        self.assertTrue(srch2 in self.searcher.active_searches)
        srch3 = self.searcher.start_search(['3'])
        self.assertTrue(srch3 in self.searcher.active_searches)

        # put the fourth, and test
        srch4 = self.searcher.start_search(['4'])
        self.assertFalse(srch1 in self.searcher.active_searches)
        self.assertTrue(srch2 in self.searcher.active_searches)
        self.assertTrue(srch3 in self.searcher.active_searches)
        self.assertTrue(srch4 in self.searcher.active_searches)

    def test_get_results_wait(self):
        """Check it waits for the search to be ready."""
        def f():
            """Trigger the results later."""
            time.sleep(.5)
            self.index.ready.set()

        threading.Thread(target=f).start()
        search_id = self.searcher.start_search(['a'])
        t = time.time()
        self.searcher.get_results(search_id)
        self.assertTrue(time.time() - t >= .5)

    def test_get_results_quantity(self):
        """Get indicated quantity."""
        # prepare the index
        self.index.fake_full.extend([1, 2, 3, 4])
        self.index.ready.set()

        # check
        search_id = self.searcher.start_search(['a'])
        results = self.searcher.get_results(search_id, quantity=3)
        self.assertEqual(results, [1, 2, 3])

    def test_get_results_start(self):
        """Get from a result."""
        # prepare the index
        self.index.fake_full.extend([1, 2, 3, 4])
        self.index.ready.set()

        # check
        search_id = self.searcher.start_search(['a'])
        results = self.searcher.get_results(search_id, start=2)
        self.assertEqual(results, [3, 4])

    def test_get_across_types(self):
        """Get from complete and partial."""
        # prepare the index
        self.index.fake_full.extend([1, 2, 3, 4])
        self.index.fake_partial.extend([5, 6, 7, 8])
        self.index.ready.set()

        # check
        search_id = self.searcher.start_search(['a'])
        results = self.searcher.get_results(search_id, quantity=3)
        self.assertEqual(results, [1, 2, 3])
        results = self.searcher.get_results(search_id, start=3, quantity=3)
        self.assertEqual(results, [4, 5, 6])
        results = self.searcher.get_results(search_id, start=6, quantity=3)
        self.assertEqual(results, [7, 8])

    def test_get_repeated(self):
        """Get same info several times."""
        # prepare the index
        self.index.fake_full.extend([1, 2, 3, 4])
        self.index.fake_partial.extend([5, 6, 7, 8])
        self.index.ready.set()

        # check
        search_id = self.searcher.start_search(['a'])
        results = self.searcher.get_results(search_id, quantity=3)
        self.assertEqual(results, [1, 2, 3])
        results = self.searcher.get_results(search_id, start=2, quantity=5)
        self.assertEqual(results, [3, 4, 5, 6, 7])
        results = self.searcher.get_results(search_id, start=4)
        self.assertEqual(results, [5, 6, 7, 8])

    def test_discard_item(self):
        """Check that sets the search to stop."""
        self.index.ready.set()
        search_id = self.searcher.start_search(['words'])
        real_search, results, _, _ = self.searcher.active_searches[search_id]
        assert not real_search.discarded

        # do three more searchs to discard the first one
        for i in xrange(3):
            self.searcher.start_search([str(i)])

        self.assertTrue(real_search.discarded)

    def test_hanging_bug(self):
        """Test taken from issue 140."""
        self.index.ready.set()

        _id = self.searcher.start_search(['words'])
        self.searcher.get_results(_id)
        self.searcher.get_results(_id)


class CacheTestCase(unittest.TestCase):
    """Tests for the Cache."""

    def setUp(self):
        """Set up."""
        self.cache = Cache(3, lambda *_: None)

    def test_set_simple(self):
        """Add one item."""
        self.cache['a'] = 3
        self.assertTrue('a' in self.cache)
        self.cache['b'] = 5
        self.assertTrue('b' in self.cache)

    def test_set_overflow(self):
        """Add one item over the limit."""
        # get to the limit
        self.cache['a'] = 1
        self.cache['b'] = 2
        self.cache['c'] = 3

        # pass it
        self.cache['d'] = 4
        self.assertFalse('a' in self.cache)
        self.assertTrue('b' in self.cache)
        self.assertTrue('c' in self.cache)
        self.assertTrue('d' in self.cache)

    def test_set_repeated(self):
        """Check behaviour when adding repeated value."""
        self.cache['a'] = 1
        self.cache['a'] = 2
        self.assertEqual(len(self.cache._items), 1)

    def test_delete(self):
        """Check internal maintenance when deleting."""
        self.cache['a'] = 1
        self.assertEqual(len(self.cache._items), 1)
        del self.cache['a']
        self.assertEqual(len(self.cache._items), 0)

    def test_discard(self):
        """Check it calls the discarding function."""
        # overwrite function, to check
        discarded = []
        self.cache._discard_func = lambda *a: discarded.extend(a)

        # put 4 values, first will be discarded
        for i in xrange(4):
            self.cache['key' + str(i)] = 'item' + str(i)

        self.assertEqual(discarded, ['item0'])
