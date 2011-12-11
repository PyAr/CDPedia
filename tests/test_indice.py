# -*- coding: utf8 -*-

import sys
import unittest
import tempfile
import os
import shutil

from src.armado import compressed_index
from src.armado import easy_index


class TestIndex(unittest.TestCase):
    '''Base class.'''

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def create_index(self, info):
        '''Creates an index and then opens it again to return it.'''
        self.index.create(self.tempdir, info)
        return self.index(self.tempdir)


class TestItems(TestIndex):
    '''Test the .items method.'''

    def test_nothing(self):
        '''Nothing in the index.'''
        idx = self.create_index([])
        items = list(idx.items())
        self.assertEqual(items, [])

    def test_one_item(self):
        '''Only one item.'''
        idx = self.create_index([("a", 3)])
        items = sorted(idx.items())
        self.assertEqual(items, [("a", [3])])

    def test_several_items(self):
        '''Several items stored.'''
        idx = self.create_index([("a", 3), ("b", 5)])
        items = sorted(idx.items())
        self.assertEqual(items, [("a", [3]), ("b", [5])])

    def test_same_keys(self):
        '''Two items with the same key.'''
        idx = self.create_index([("a", 3), ("a", 5)])
        items = sorted(idx.items())
        self.assertEqual(items, [("a", [3, 5])])

    def test_mixed(self):
        '''Two items with the same key and something else.'''
        idx = self.create_index([("a", 3), (u"ñ", 7), ("a", 5)])
        items = sorted(idx.items())
        self.assertEqual(items, [("a", [3, 5]), (u"ñ", [7])])


class TestValues(TestIndex):
    '''Test the .values method.'''

    def test_nothing(self):
        '''Nothing in the index.'''
        idx = self.create_index([])
        values = list(idx.values())
        self.assertEqual(values, [])

    def test_one_item(self):
        '''Only one item.'''
        idx = self.create_index([("a", 3)])
        values = sorted(idx.values())
        self.assertEqual(values, [3])

    def test_several_values(self):
        '''Several values stored.'''
        idx = self.create_index([("a", 3), ("b", 5)])
        values = sorted(idx.values())
        self.assertEqual(values, [3, 5])

    def test_same_keys(self):
        '''Two values with the same key.'''
        idx = self.create_index([("a", 3), ("a", 5)])
        values = sorted(idx.values())
        self.assertEqual(values, [3, 5])

    def test_mixed(self):
        '''Two values with the same key and something else.'''
        idx = self.create_index([(u"ñ", 3), ("b", 7), (u"ñ", 5)])
        values = sorted(idx.values())
        self.assertEqual(values, [3, 5, 7])


class TestRandom(TestIndex):
    '''Test the .random method.'''

    def test_one_item(self):
        '''Only one item.'''
        idx = self.create_index([("a", 3)])
        value = idx.random()
        self.assertEqual(value, 3)

    def test_several_values(self):
        '''Several values stored.'''
        idx = self.create_index([("a", 3), ("b", 5)])
        value = idx.random()
        self.assertTrue(value in (3, 5))


class TestContains(TestIndex):
    '''Test the "in" functionality.'''

    def test_nothing(self):
        '''Nothing in the index.'''
        idx = self.create_index([])
        self.assertFalse("a" in idx)

    def test_one_item(self):
        '''Only one item.'''
        idx = self.create_index([("a", 3)])
        self.assertTrue("a" in idx)
        self.assertFalse("b" in idx)

    def test_several_values(self):
        '''Several values stored.'''
        idx = self.create_index([("a", 3), (u"ñ", 5)])
        self.assertTrue("a" in idx)
        self.assertTrue(u"ñ" in idx)
        self.assertFalse("c" in idx)


class TestSearch(TestIndex):
    '''Test the .search method.'''

    def test_nothing(self):
        '''Nothing in the index.'''
        idx = self.create_index([])
        res = idx.search(["a"])
        self.assertEqual(list(res), [])

    def test_one_item(self):
        '''Only one item.'''
        idx = self.create_index([("a", 3)])
        res = idx.search(["a"])
        self.assertEqual(list(res), [3])
        res = idx.search(["b"])
        self.assertEqual(list(res), [])

    def test_several_values(self):
        '''Several values stored.'''
        idx = self.create_index([("a", 3), ("b", 5)])
        res = idx.search(["a"])
        self.assertEqual(list(res), [3])
        res = idx.search(["b"])
        self.assertEqual(list(res), [5])
        res = idx.search(["c"])
        self.assertEqual(list(res), [])

    def test_same_keys(self):
        '''Two values with the same key.'''
        idx = self.create_index([("a", 3), ("a", 5)])
        res = idx.search(["a"])
        self.assertEqual(list(res), [3, 5])
        res = idx.search(["b"])
        self.assertEqual(list(res), [])

    def test_mixed(self):
        '''Two values with the same key and something else.'''
        idx = self.create_index([("a", 3), (u"ñ", 7), ("a", 5)])
        res = idx.search(["a"])
        self.assertEqual(list(res), [3, 5])
        res = idx.search([u"ñ"])
        self.assertEqual(list(res), [7])
        res = idx.search(["c"])
        self.assertEqual(list(res), [])

    def test_nopartial(self):
        '''Does not find partial values.'''
        idx = self.create_index([("aa", 3)])
        res = idx.search(["a"])
        self.assertEqual(list(res), [])

    def test_and(self):
        '''Check that AND is applied.'''
        idx = self.create_index([("a", 3), ("b", 3), ("a", 5), ("c", 5)])
        res = idx.search(["a", "b"])
        self.assertEqual(list(res), [3])
        res = idx.search(["b", "c"])
        self.assertEqual(list(res), [])


class TestPartialSearch(TestIndex):
    '''Test the .partial_search method.'''

    def test_nothing(self):
        '''Nothing in the index.'''
        idx = self.create_index([])
        res = idx.partial_search(["a"])
        self.assertEqual(list(res), [])

    def test_prefix(self):
        '''Match its prefix.'''
        idx = self.create_index([(u"abñc", 3)])
        res = idx.partial_search(["ab"])
        self.assertEqual(list(res), [3])
        res = idx.partial_search(["ad"])
        self.assertEqual(list(res), [])

    def test_suffix(self):
        '''Match its suffix.'''
        idx = self.create_index([(u"abñd", 3)])
        res = idx.partial_search([u"ñd"])
        self.assertEqual(list(res), [3])
        res = idx.partial_search(["ad"])
        self.assertEqual(list(res), [])

    def test_middle(self):
        '''Match in the middle.'''
        idx = self.create_index([(u"abñd", 3)])
        res = idx.partial_search([u"bñ"])
        self.assertEqual(list(res), [3])
        res = idx.partial_search(["cb"])
        self.assertEqual(list(res), [])

    def test_exact(self):
        '''Exact match.'''
        idx = self.create_index([("abcd", 3)])
        res = idx.partial_search(["abcd"])
        self.assertEqual(list(res), [3])

    def test_several_values(self):
        '''Several values stored.'''
        idx = self.create_index([("aa", 3), ("bc", 5), ("dbj", 7), ("ab", 9)])
        res = idx.partial_search(["a"])
        self.assertEqual(list(res), [3, 9])
        res = idx.partial_search(["b"])
        self.assertEqual(list(res), [5, 7, 9])
        res = idx.partial_search(["c"])
        self.assertEqual(list(res), [5])
        res = idx.partial_search(["d"])
        self.assertEqual(list(res), [7])

    def test_and(self):
        '''Check that AND is applied.'''
        idx = self.create_index([("oao", 3), ("bll", 3),
                                 ("nga", 5), ("xxc", 5), ("ooa", 7)])
        res = idx.partial_search(["a", "b"])
        self.assertEqual(list(res), [3])
        res = idx.partial_search(["b", "c"])
        self.assertEqual(list(res), [])
        res = idx.partial_search(["a", "o"])
        self.assertEqual(list(res), [3, 7])


class TestCreate(TestIndex):
    '''Test the .create method in the non-working cases.'''

    def test_non_iterable(self):
        '''It must iterate on what receives.'''
        self.assertRaises(TypeError, self.index.create, self.tempdir, None)

    def test_key_string(self):
        '''Keys can be string.'''
        self.index.create(self.tempdir, [("aa", 33)])

    def test_key_unicode(self):
        '''Keys can be unicode.'''
        self.index.create(self.tempdir, [(u"año", 33)])

    def test_key_badtype(self):
        '''Keys must be strings or unicode.'''
        self.assertRaises(TypeError, self.index.create, self.tempdir, [(1, 3)])

    def test_return_quantity(self):
        '''Must return the quantity indexed.'''
        q = self.index.create(self.tempdir, [])
        self.assertEqual(q, 0)
        q = self.index.create(self.tempdir, [("a", 1)])
        self.assertEqual(q, 1)
        q = self.index.create(self.tempdir, [("a", 1), ("b", 2)])
        self.assertEqual(q, 2)
        q = self.index.create(self.tempdir, [("a", 1), ("a", 2)])
        self.assertEqual(q, 2)

_testcases = [TestIndex, TestItems, TestValues, TestRandom, TestContains,
              TestSearch, TestPartialSearch, TestCreate]

# Para correr los tests de los distintos indices (compressed y easy) y no duplicar
# las clases de los tests, generamos las clases dinamicamente con la funcion/metaclase
# indexed_testcase

def indexed_testcase(testcase, name, index):
    new_testcase = type(testcase.__name__ + name, (testcase, ), {})
    new_testcase.index = index
    return new_testcase

_compressed_testcases = [indexed_testcase(testcase, "Compressed", \
                                          compressed_index.Index) \
                                                  for testcase in _testcases]
_easy_testcases = [indexed_testcase(testcase, "Easy", easy_index.Index) \
                                                  for testcase in _testcases]

_all_testcases = _compressed_testcases + _easy_testcases

def suite():
    suite = unittest.TestSuite()
    for test_case in _all_testcases:
        suite.addTest(unittest.makeSuite(test_case))
    return suite

def load_tests(loader, tests, pattern):
    return suite()

if __name__ == '__main__':
    unittest.main(defaultTest="suite")
