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

import operator
import os
import pickle
import random
from bz2 import BZ2File as CompressedFile
from functools import lru_cache, reduce

from src import utiles


class Index(object):
    '''Handles the index.'''

    def __init__(self, directory):
        self._directory = directory

        # open the key shelve
        keyfilename = os.path.join(directory, "easyindex.key.bz2")
        fh = CompressedFile(keyfilename, "rb")
        self.key_shelf = pickle.load(fh)
        fh.close()

        # see how many id files we have
        filenames = []
        for fn in os.listdir(directory):
            if fn.startswith("easyindex-") and fn.endswith(".ids.bz2"):
                filenames.append(fn)
        self.idfiles_count = len(filenames)

    @lru_cache(20)
    def _get_ids_shelve(self, cual):
        '''Return the ids index.'''
        fname = os.path.join(self._directory, "easyindex-%03d.ids.bz2" % cual)
        fh = CompressedFile(fname, "rb")
        idx = pickle.load(fh)
        fh.close()
        return idx

    def _get_info_id(self, allids):
        '''Returns the values for the given ids.

        As it groups the ids according to the file, is much faster than
        retrieving one by one.
        '''
        # group the id per file
        cuales = {}
        for i in allids:
            cual = utiles.coherent_hash(i) % self.idfiles_count
            cuales.setdefault(cual, []).append(i)

        # get the info for each file
        for cual, ids in cuales.items():
            idx = self._get_ids_shelve(cual)
            for i in ids:
                yield idx[i]

    def keys(self):
        """Returns an iterator over the stored keys."""
        return iter(self.key_shelf.keys())

    def items(self):
        '''Returns an iterator over the stored items.'''
        for key, allids in self.key_shelf.items():
            values = self._get_info_id(allids)
            yield key, sorted(values)

    def values(self):
        '''Returns an iterator over the stored values.'''
        for key, allids in self.key_shelf.items():
            values = self._get_info_id(allids)
            for v in values:
                yield v

    def random(self):
        '''Returns a random value.'''
        cual = random.randint(0, self.idfiles_count - 1)
        idx = self._get_ids_shelve(cual)
        return random.choice(list(idx.values()))

    def __contains__(self, key):
        '''Returns if the key is in the index or not.'''
        return key in self.key_shelf

    def _merge_results(self, results):
        # vemos si tenemos algo más que vacio
        results = list(filter(bool, results))
        if not results:
            return []

        # el resultado final es la intersección de los parciales ("and")
        intersectados = reduce(operator.iand, (set(d) for d in results))
        final = {}
        for result in results:
            for pagtit, ptje in result.items():
                if pagtit in intersectados:
                    final[pagtit] = final.get(pagtit, 0) + ptje

        final = [(pag, tit, ptje) for (pag, tit), ptje in final.items()]
        return sorted(final, key=operator.itemgetter(2), reverse=True)

    def search(self, keys):
        '''Returns all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        '''
        results = []
        for key in keys:
            if key not in self.key_shelf:
                continue
            allids = self.key_shelf[key]
            results.append(allids)

        if not results:
            return []

        # do AND between results, and get the values from ids
        intersectados = reduce(operator.iand, results)
        allvals = self._get_info_id(intersectados)
        return allvals

    def partial_search(self, keys):
        '''Returns all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        '''
        results = []
        for key_search in keys:
            # the partial result starts with an empty set, that will be
            # filled in the OR reduce
            partial_res = [set()]

            # search in all the keys, for partial match
            for key_stored, allids in self.key_shelf.items():
                if key_search in key_stored:
                    partial_res.append(allids)

            # for the same key searched, we do OR to the results
            unidos = reduce(operator.ior, partial_res)
            results.append(unidos)

        if not results:
            return []

        # do AND between results, and get the values from ids
        intersectados = reduce(operator.iand, results)
        allvals = self._get_info_id(intersectados)
        return allvals

    @classmethod
    def create(cls, directory, source):
        '''Creates the index in the directory.

        The "source" generates pairs (key, value) to store in the index.  The
        key must be a string, the value can be any hashable Python object.

        It must return the quantity of pairs indexed.
        '''
        ids_shelf = {}
        key_shelf = {}
        ids_cnter = 0
        tmp_reverse_id = {}
        indexed_counter = 0

        # fill them
        for key, value in source:
            indexed_counter += 1

            # process key
            if not isinstance(key, str):
                raise TypeError("The key must be string or unicode")

            # docid -> info final
            if value in tmp_reverse_id:
                docid = tmp_reverse_id[value]
            else:
                docid = str(ids_cnter).encode("ascii")
                tmp_reverse_id[value] = docid
                ids_cnter += 1
            ids_shelf[docid] = value

            # keys -> docid
            key_shelf.setdefault(key, set()).add(docid)

        # save key
        keyfilename = os.path.join(directory, "easyindex.key.bz2")
        fh = CompressedFile(keyfilename, "wb")
        pickle.dump(key_shelf, fh, 2)
        fh.close()

        # split ids_shelf in N dicts of about ~5k entries
        N = int(round(len(ids_shelf) / 5000.0))
        if not N:
            N = 1
        all_idshelves = [{} for i in range(N)]
        for k, v in ids_shelf.items():
            cual = utiles.coherent_hash(k) % N
            all_idshelves[cual][k] = v

        # save dict where corresponds
        for cual, shelf in enumerate(all_idshelves):
            fname = "easyindex-%03d.ids.bz2" % cual
            idsfilename = os.path.join(directory, fname)
            fh = CompressedFile(idsfilename, "wb")
            pickle.dump(shelf, fh, 2)
            fh.close()

        return indexed_counter
