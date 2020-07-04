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
import logging
import os
from functools import lru_cache
import random
import sqlite3

from src import utiles
logger = logging.getLogger(__name__)

MAX_IDX_FIELDS = 8


def _idxtable_fields(mask="?"):
    mask = mask.replace("?", "%s")
    replac = ', '.join([mask % field for field in ["docid%02d", "score%02d"]])
    return ','.join([replac % (d +1, d +1) for d in range(MAX_IDX_FIELDS)])


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
        return cur.fetchall()[0]

    def _search_asoc_docs(self, keys):
        """Returns all asociated docs ids from a word's set."""
        marks = ', '.join(["?"] * len(keys))
        sql = "select * from asoc_docs "
        sql += f" where word in ({marks})"
        cur = self.db.execute(sql, keys)
        for row in cur.fetchall():
            docsid = zip(row[2::2], row[3::2])
            dicc = {k: v for k, v in docsid if k is not None and k != 'null'}
            yield row[0], dicc

    def _search_merge_results(self,source):
        """Compute the set of results with all identified keys."""
        prev = None
        added = None
        for word, dicc in source:
            if word != prev:
                if not added is None:
                    yield prev, added
                added = dicc
                prev = word
            else:
                added.update(dicc)
        yield prev, added

    def _search_order_items(self, source):
        """ Order the resuls by scores."""
        results = {}
        for word, dicc in source:
            if results:
                cj = set(results.keys()) & set(dicc.keys())
                res = {k: results[k] + dicc[k] for k in cj}
                results = res
            else:
                results = dicc

        to_list = [(v, k) for k, v in results.items()]
        to_list.sort(reverse=True)
        return to_list

    def search(self, keys):
        '''Returns all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        '''

        data = self._search_asoc_docs(keys)
        founded = self._search_merge_results(data)
        ordered = self._search_order_items(founded)
        for _, ndoc in ordered:
            yield self.get_doc(ndoc)

    def partial_search(self, keys):
        '''Returns all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        '''
        pass

    @classmethod
    def create(cls, directory, source):
        '''Creates the index in the directory.
        The source must give path, page_score, title and
        a list of extracted words from title in an ordered fashion

        It must return the quantity of pairs indexed.
        '''
        class SQLmany():
            BUFFER_SIZE = 400
            def __init__(self, name, sql):
                self.values = []
                self.name = name
                dict_stats[name] = 0
                self.sql = sql
                self.count = 0

            def add_args(self, args):
                self.values.append(args)
                self.count += 1
                logger.debug("Adding to %s: %r" % (self.name, args))
                if self.count % self.BUFFER_SIZE == 0:
                    database.executemany(self.sql, self.values)
                    database.commit()
                    self.values = []
                if self.count % 1000 == 0:
                    print(".", end="", flush=True)

            def finish(self):
                if self.values:
                    database.executemany(self.sql, self.values)
                    database.commit()
                print(self.name, ":", self.count, flush=True)
                dict_stats[self.name] = self.count

        def show_stats():
            """Finally, show some statistics."""
            for k, v in dict_stats.items():
                logger.info("{:>15}:{}".format(k,v))

        def create_database():
            """Creates de basic structure of new database."""
            database.execute("PRAGMA JOURNAL_MODE = off") #Not allow transactions until end
            index_fields = _idxtable_fields("? INTEGER")
            tables = ["CREATE TABLE tokens (tokenid INTEGER PRIMARY KEY, word TEXT, " +\
                      "results INTEGER, docid00 INTEGER, score00 INTEGER);",
                "CREATE TABLE docs (docid INTEGER PRIMARY KEY, namhtml TEXT, pagescore INTEGER);",
                "CREATE TABLE idxtable (tokenid INTEGER, %s); " % index_fields]
            for table in tables:
                database.execute(table)
            database.commit()

        def value_words_by_position(words):
            word_scores = {}
            if len(words) <= 1:
                decrement = 0
                ratio = 100
            else:
                decrement = (70 - 30) // len(words)
                ratio = 100 // len(words)
            for pos, word in enumerate(words):
                word_score = ratio * (100 - decrement * (1 + pos))
                word_scores[word] = word_score // 1000
            logger.debug("Word scores %r" % word_scores)
            return word_scores

        def add_docs_keys(source):
            """Add docs and keys registers to db and its rel in memory."""
            idx_dict = {}
            sql_page = "insert into docs (docid, namhtml, pagescore) values (?, ?, ?)"
            buffer = SQLmany("Documents", sql_page)
            for docid, (words, namhtml, page_score) in enumerate(source):
                # first insert the new page
                cursor = database.cursor()
                buffer.add_args((docid, namhtml, page_score))
                add_words(idx_dict, words, docid, page_score)
            buffer.finish()
            return idx_dict

        def add_words(idx_dict, words, docid, page_score):
            word_scores = value_words_by_position(words)
            for word, word_score in word_scores.items():
                item = (max(1, word_score * page_score // 100), docid)
                if word in idx_dict:
                    idx_dict[word].append(item)
                else:
                    idx_dict[word] = [item]

        def add_tokens_to_db(idx_dict):
            sql_ins = "insert into tokens (tokenid, word, results, score00, docid00) values (?, ?, ?, ?, ?)"
            index_fields = _idxtable_fields()
            sql_add = "insert into idxtable (tokenid, %s) values (%s)"
            sql_add = sql_add % (index_fields, ','.join(["?"] * (MAX_IDX_FIELDS * 2 + 1) ))
            buffer_t = SQLmany("Tokens", sql_ins)
            buffer_r = SQLmany("Relationships", sql_add)
            for tokenid, (word, docs_list) in enumerate(idx_dict.items()):
                docs_list.sort(reverse=True)
                buffer_t.add_args((tokenid, word, len(docs_list),
                                   docs_list[0][0], docs_list[0][1]))
                if len(docs_list) > 1:
                    add_other_relations(buffer_r, tokenid, docs_list[1:])
            buffer_t.finish()
            buffer_r.finish()

        def add_other_relations(buffer_r, tokenid, asoc_docs):
            tot_asoc = len(asoc_docs)
            for n_page in range(0, tot_asoc, MAX_IDX_FIELDS):
                args = [tokenid]
                for idx in range(n_page, min(n_page + MAX_IDX_FIELDS, tot_asoc)):
                    args.extend([asoc_docs[idx][1], asoc_docs[idx][0]])
                missing = (MAX_IDX_FIELDS * 2 + 1) - len(args)
                if missing:
                    args.extend(["null"] * missing)
                buffer_r.add_args(args)

        def create_idx_querys():
            index_fields = _idxtable_fields("i.?")
            queries = ["create index idx_words on tokens (word, results)",
                       "create index idx_table on idxtable (tokenid)",
                       "vacuum"]
            view = ["create view asoc_docs as select",
                    "t.word, t.results, t.docid00, t.score00,",
                    index_fields,
                    "from tokens as t left join idxtable as i",
                    "on i.tokenid = t.tokenid order by results"]
            queries.append(' '.join(view))
            for sql in queries:
                database.execute(sql)
            database.commit()

        logger.info("Indexing")
        import timeit
        initial_time = timeit.default_timer()
        dict_stats = {}
        idx = Index(directory)
        database = idx.db
        create_database()
        idx_dict = add_docs_keys(source)
        add_tokens_to_db(idx_dict)
        create_idx_querys()
        logger.info("Total time: %r" % int(timeit.default_timer() - initial_time))
        show_stats()
