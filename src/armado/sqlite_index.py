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
from functools import lru_cache
import random
import sqlite3

from src import utiles


MAX_IDX_FIELDS = 10


def _idxtable_fields(add_type=False):
    if add_type:
        mask =   "docid%02d INTEGER, score%02d INTEGER"
    else:
        mask =   "docid%02d, score%02d"
    return ','.join([mask % (d, d) for d in range(MAX_IDX_FIELDS)])


class Index(object):
    '''Handles the index.'''

    def __init__(self, directory):
        self._directory = directory
        keyfilename = os.path.join(directory, "index.sqlite")
        self.db = sqlite3.connect(keyfilename)

    def _token_ids(self, words):
        """Returns a dict with words and its rowid."""
        prev = ', '.join(["?"] * len(words))
        sql_prev = f"select rowid, word from tokens where word in ({prev})"
        in_db = self.db.execute(sql_prev, words)
        in_db = list(in_db.fetchall())
        return {row[1]:row[0] for row in in_db}

    def keys(self):
        """Returns an iterator over the stored keys."""
        cur = self.db.execute("SELECT word FROM tokens")
        return [row[0] for row in cur.fetchall()]

    def items(self):
        '''Returns an iterator over the stored items.'''
        cur = self.db.execute("SELECT rowid, namhtml, pagescore FROM docs")
        return cur.fetchall()

    def values(self):
        '''Returns an iterator over the stored values.'''
        pass

    def random(self):
        '''Returns a random value.'''
        pass

    def __contains__(self, key):
        '''Returns if the key is in the index or not.'''
        pass

    def _merge_results(self, results):
        pass

    def get_doc(self, docid):
        '''Returns an iterator over the stored items.'''
        cur = self.db.execute("SELECT namhtml, pagescore FROM docs where rowid = ?", (docid,))
        return cur.fetchall()

    def search(self, keys):
        '''Returns all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        '''

        tokens = self._token_ids(keys)
        ids = ', '.join(["?"] * len(tokens))
        sql = "select token, results, "
        sql += _idxtable_fields()
        sql += " from idxtable"
        sql += f" where token in ({ids})"
        sql += " order by token"
        cur = self.db.execute(sql,list(tokens.values()))
        items = []
        values = []
        prev = ''
        for row in cur.fetchall():
            docsid = row[2::2]
            v = list(zip(docsid, row[3::2]))
            items.extend(v)
            if prev == row[0]:
                values[-1] += set(docsid)
            else:
                values.append(set(docsid))
            prev = row[0]
        conj = values[0] - set([0])
        for n in values[1:]:
            conj -= n
        results = {}
        print('conj', conj)
        for docid, value in items:
            if docid in conj:
                results[docid] = results.get(docid, 0) + value
        to_list = [(v,k) for k,v in results.items()]
        to_list.sort(reverse=True)
        for _, ndoc in to_list:
            yield self.get_doc(ndoc)

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
            for key_stored, allids in self.key_shelf.iteritems():
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
        The source must give path, page_score, title and
        a list of extracted words from title in an ordered fashion

        It must return the quantity of pairs indexed.
        '''
        index_fields = ','.join(["docid%02d INTEGER, score%02d INTEGER " % (d, d) for d in range(MAX_IDX_FIELDS)])
        tables = ["CREATE TABLE IF NOT EXISTS tokens (word TEXT PRIMARY KEY);",
            "CREATE TABLE IF NOT EXISTS docs (namhtml TEXT, pagescore INTEGER);",
            "CREATE TABLE IF NOT EXISTS idxtable (token INTEGER, results INTEGER, %s); " % index_fields]

        idx = Index(directory)
        database = idx.db
        for table in tables:
            database.execute(table)
        database.commit()
        idx_dict = {}
        for words, namhtml, page_score in source:
            # first insert the new page
            sql_page = "insert into docs (namhtml, pagescore) values (?, ?)"
            cursor = database.cursor()
            cursor.execute(sql_page, (namhtml, page_score))
            docid = cursor.lastrowid

            # check for missing words in database
            tokens = idx._token_ids(words)
            missing = set(words) - set(tokens.keys())
            if missing:
                #add missing words to database
                sql_ins = "insert into tokens (word) values (?)"
                database.executemany(sql_ins, [[word] for word in missing])
                database.commit()
                tokens = idx._token_ids(words)
            else:
                database.commit()
            for tokenid in tokens.values():
                if tokenid in idx:
                    idx_dict[tokenid].append((docid, 0))
                else:
                    idx_dict[tokenid] = [(docid,0)]

        index_fields = _idxtable_fields()
        sql_add = "insert into idxtable (token, results, %s) values (%s)"
        sql_add = sql_add % (index_fields, ','.join(["?"] * (MAX_IDX_FIELDS * 2 + 2) ))
        for tokenid, asoc_docs in idx_dict.items():
            tot_asoc = len(asoc_docs)
            if tot_asoc % MAX_IDX_FIELDS == 0:
                reg_count = tot_asoc // MAX_IDX_FIELDS
            else:
                reg_count = 1 + tot_asoc // MAX_IDX_FIELDS
                add_slots = (reg_count * MAX_IDX_FIELDS) - tot_asoc
                asoc_docs.extend([(0,0)] * add_slots)
            for n in range(reg_count):
                values = asoc_docs[n * MAX_IDX_FIELDS: (n+1) * MAX_IDX_FIELDS]
                use_v = [tokenid, tot_asoc]
                for asoc_doc in asoc_docs:
                    use_v.extend(asoc_doc)
                database.execute(sql_add, use_v)
            database.commit()
