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


import array
import pickle
import zlib
import logging
import os
import random
import sqlite3
from functools import lru_cache

from src import utiles
logger = logging.getLogger(__name__)

MAX_IDX_FIELDS = 8
PAGE_SIZE = 1024
page_fn = lambda id: divmod(id, PAGE_SIZE)
decompress_data = lambda d: pickle.loads(zlib.decompress(d))



def delta_encode(docset, sorted=sorted, with_reps=False):
    """Compress an array of numbers into a bytes object.

    - docset is an array of long integers, it contain the begin position
      of every word in the set.
    - sorted is a sorting function, it must be a callable
    - with_reps is True on search, but false on creation.
    """
    pdoc = -1
    rv = array.array('B')
    rva = rv.append
    flag = (0, 0x80)
    for doc in sorted(docset):
        if with_reps or doc != pdoc:
            if not with_reps and doc <= pdoc:
                # decreasing sequence element escaped by 0 delta entry
                rva(0)
                pdoc = -1
            doc, pdoc = doc - pdoc, doc
            while True:
                b = doc & 0x7F  # copies to b the last 7 bits on doc
                doc >>= 7  # to right 7 bits doc number
                b |= flag[doc != 0]  # add 0x80 (128, 2^7) if doc is greater
                rva(b)
                if not doc:
                    break  # if doc is zero, stop, else add another byte to this entry
    return rv.tobytes()


def delta_decode(docset, ctor=set, append="add", with_reps=False):
    """Decode a compressed encoded bucket.

    - docset is a bytes object, representing a byte's array
    - ctor is the final container
    - append is the callable attribute used to add an element into the ctor
    - with_reps is used on unpickle.
    """
    doc = 0
    pdoc = -1
    rv = ctor()
    rva = getattr(rv, append)
    shif = 0
    abucket = array.array('B')
    abucket.frombytes(docset)
    for b in abucket:
        doc |= (b & 0x7F) << shif
        shif += 7
        if not (b & 0x80):
            if doc == 0 and not with_reps:
                # 0 delta entry encodes a sequence reset command
                pdoc = -1
            else:
                pdoc += doc
                rva(pdoc)
            doc = shif = 0
    return rv


class Index(object):
    '''Handles the index.'''

    def __init__(self, directory):
        self._directory = directory
        keyfilename = os.path.join(directory, "index.sqlite")
        self.db = sqlite3.connect(keyfilename)

    def _token_ids(self, words):
        """Returns a dict with words and its rowid."""
        prev = ', '.join(["?"] * len(words))
        sql_prev = f"select tokenid, word from tokens where word in ({prev})"
        in_db = self.db.execute(sql_prev, words)
        in_db = list(in_db.fetchall())
        return {row[1]:row[0] for row in in_db}

    def keys(self):
        """Returns an iterator over the stored keys."""
        cur = self.db.execute("SELECT word FROM tokens")
        return [row[0] for row in cur.fetchall()]

    def items(self):
        '''Returns an iterator over the stored items.'''
        for key in self.keys():
            _, dicc = self._search_asoc_docs(key)
            for docid, score in dicc.items():
                yield self.get_doc(docid)

    def values(self):
        '''Returns an iterator over the stored values.'''
        cur = self.db.execute("SELECT pageid, data FROM docs ORDER BY pageid")
        for row in cur.fetchall():
            decomp_data = decompress_data(row[1])
            for doc in decomp_data:
                yield doc

    @lru_cache
    def __len__(self):
        sql = 'Select pageid, data from docs order by pageid desc limit 1'
        cur = self.db.execute(sql)
        row = cur.fetchone()
        decomp_data = decompress_data(row[1])
        return row[0] * PAGE_SIZE + len(decomp_data)

    def random(self):
        '''Returns a random value.'''
        docid = random.randint(0, len(self) - 1)
        return self.get_doc(docid)

    def __contains__(self, key):
        '''Returns if the key is in the index or not.'''
        cur = self.db.execute("SELECT word FROM tokens where word = ?", (key,))
        if cur.fetchone():
            return True
        return False

    @lru_cache
    def _get_page(self, pageid):
        cur = self.db.execute("SELECT data FROM docs where pageid = ?", (pageid,))
        row = cur.fetchone()
        if row:
            decomp_data = decompress_data(row[0])
            return decomp_data
        return None

    def get_doc(self, docid):
        '''Returns an iterator over the stored items.'''
        page_id, rel_id = page_fn(docid)
        data = self._get_page(page_id)
        if data:
            return data[docid % PAGE_SIZE]
        return None

    def _search_asoc_docs(self, keys):
        """Returns all asociated docs ids from a word's set."""
        marks = ', '.join(["?"] * len(keys))
        sql = "select word, results, docid, score from tokens"
        sql += f" where word in ({marks})"
        cur = self.db.execute(sql, tuple(keys))
        return cur.fetchall()

    def _search_decode_asoc_docs(self, source):
        for row in source:
            docsid = delta_decode(row[2])
            scores = array.array('B')
            scores.frombytes(row[3])
            dicc = dict(zip(docsid, scores))
            yield row[0], dicc

    def _search_order_items(self, source):
        """Merge & order the resuls by scores."""
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

        cur = self._search_asoc_docs(keys)
        decoded = self._search_decode_asoc_docs(cur)
        ordered = self._search_order_items(decoded)
        for _, ndoc in ordered:
            yield self.get_doc(ndoc)

    def partial_search(self, keys):
        '''Returns all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        '''
        founded = set()
        for key in keys:
            sql = "SELECT word FROM tokens WHERE word LIKE ?"
            cur = self.db.execute(sql, (f"%%{key}%%",))
            if cur:
                founded |= set([r[0] for r in cur if not r[0] in keys])
        return self.search(founded)

    @classmethod
    def create(cls, directory, source, show_progress=True):
        '''Creates the index in the directory.
        The source must give path, page_score, title and
        a list of extracted words from title in an ordered fashion

        It must return the quantity of pairs indexed.
        '''
        import pickletools
        class ManyInserts():
            def __init__(self, name, sql, buff_size):
                self.sql = sql
                self.name = name
                self.buff_size = buff_size
                self.count = 0
                self.buffer = []

            def append(self, data):
                self.buffer.append(data)
                self.count +=1
                if self.count % self.buff_size == 0:
                    self.persists()
                    self.buffer = []
                if cls.show_progress and self.count % 1000 == 0:
                    print(".", end="", flush=True)

            def finish(self):
                """Finish the process and prints some data."""
                if self.buffer:
                    self.persists()
                if cls.show_progress:
                    print(self.name, ":", self.count, flush=True)
                dict_stats[self.name] = self.count

            def persists(self):
                pass


        class Compressed(ManyInserts):
            """Creates the table of compressed documents information.
            The groups is PAGE_SIZE lenght, pickled and compressed"""
            def persists(self):
                """Compress and commit data to index."""
                pickdata = pickletools.optimize(pickle.dumps(self.buffer))
                comp_data = zlib.compress(pickdata, level=9)
                database.execute(self.sql,
                                 (page_fn(self.count - 1)[0],
                                 comp_data))
                database.commit()

        class SQLmany(ManyInserts):
            """Execute many INSERTs greatly improves the performance."""
            def persists(self):
                """Commit data to index."""
                database.executemany(self.sql, self.buffer)
                database.commit()

        def show_stats():
            """Finally, show some statistics."""
            for k, v in dict_stats.items():
                logger.info("{:>15}:{}".format(k,v))

        def create_database():
            """Creates de basic structure of new database."""
            tables = ["PRAGMA JOURNAL_MODE = off",
                      "CREATE TABLE tokens (tokenid INTEGER PRIMARY KEY, word TEXT, " +\
                      "results INTEGER, docid BLOB, score BLOB);",
                      "CREATE TABLE docs (pageid INTEGER PRIMARY KEY, data BLOB);"]
            for table in tables:
                database.execute(table)
                database.commit()

        def value_words_by_position(words):
            """The word's relative importance in sentence."""
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
            sql = "INSERT INTO docs (pageid, data) VALUES (?, ?)"
            docs_table = Compressed("Documents", sql, PAGE_SIZE)
            for docid, (words, page_score, data) in enumerate(source):
                # first insert the new page
                docs_table.append(list(data) + [page_score])
                add_words(idx_dict, words, docid, page_score)
            docs_table.finish()
            return idx_dict

        def add_words(idx_dict, words, docid, page_score):
            """Stores in a dict the words and its related documents."""
            word_scores = value_words_by_position(words)
            for word, word_score in word_scores.items():
                item = (docid, max(1, word_score * page_score // 100))
                cls.max_word_score = max(cls.max_word_score, item[1])
                if word in idx_dict:
                    idx_dict[word].append(item)
                else:
                    idx_dict[word] = [item]

        def add_tokens_to_db(idx_dict):
            """Insert token words in the database."""
            sql_ins = "insert into tokens (tokenid, word, results, docid, score) values (?, ?, ?, ?, ?)"
            buffer_t = SQLmany("Tokens", sql_ins, 400)
            unit = cls.max_word_score / 255
            norm_score = lambda v: int(v[1] / unit)
            dict_stats["Indexed"] = 0
            for tokenid, (word, docs_list) in enumerate(idx_dict.items()):
                docs_list.sort()
                docs = [v[0] for v in docs_list]
                docs_enc = delta_encode(docs)
                scores = array.array("B")
                scores.extend(map(norm_score, docs_list))
                dict_stats["Indexed"] += len(docs_list)
                buffer_t.append((tokenid, word, len(docs_list),
                                   docs_enc, scores.tobytes()))
            buffer_t.finish()

        def create_indexes():
            queries = ["create index idx_words on tokens (word, results)",
                       "vacuum"]
            for sql in queries:
                database.execute(sql)
                database.commit()

        cls.show_progress = show_progress
        logger.info("Indexing")
        import timeit
        cls.max_word_score = 0
        initial_time = timeit.default_timer()
        dict_stats = {}
        idx = Index(directory)
        database = idx.db
        create_database()
        idx_dict = add_docs_keys(source)
        add_tokens_to_db(idx_dict)
        create_indexes()
        dict_stats["Total time"] = int(timeit.default_timer() - initial_time)
        show_stats()
        return dict_stats["Indexed"]
