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
import logging
import os
import pickle
import random
import sqlite3
import zlib
from collections import Counter
from functools import lru_cache

from src.armado import to3dirs

logger = logging.getLogger(__name__)

MAX_IDX_FIELDS = 8
PAGE_SIZE = 1024


def page_fn(id):
    return divmod(id, PAGE_SIZE)


def decompress_data(data):
    return pickle.loads(zlib.decompress(data))


class DocSet:
    """Data type to encode, decode & compute documents-id's sets."""
    def __init__(self, values=None, encoded=None):
        self._docs_list = {}
        self.unit = 1
        if encoded:
            self.decode(encoded)
        if values:
            for item in values:
                self.append(item[0], item[1])

    def append(self, docid, score):
        """Append an item to the docs_list."""
        self._docs_list[docid] = self._docs_list.get(docid, 0) + score

    def normalizeValues(self, unit=None):
        """Divide every doc score to avoid large numbers."""
        if not self._docs_list:
            return
        if not unit:
            unit = max(list(self._docs_list.values())) / 255

            # Cannot raise values, only lower them
            if unit <= 1:
                return
        for k, v in self._docs_list.items():
            self._docs_list[k] = max(1, min(255,
                                     int(self._docs_list[k] / unit)))

    def tolist(self):
        """Returns a sorted list of docs, by value."""
        to_list = [(v, k) for k, v in self._docs_list.items()]
        to_list.sort(reverse=True)
        return to_list

    def __ior__(self, other):
        """Union and add value to other docset."""
        ll = list(other._docs_list.keys())
        for k in ll:
            if k in self._docs_list.keys():
                self._docs_list[k] += other._docs_list[k]
            else:
                self._docs_list[k] = other._docs_list[k]
        return self

    def __iand__(self, other):
        """Intersect and add value to other docset."""
        ll = list(self._docs_list.keys())
        for k in ll:
            if k in other._docs_list.keys():
                self._docs_list[k] += other._docs_list[k]
            else:
                del self._docs_list[k]
        return self

    def __len__(self):
        return len(self._docs_list)

    def __repr__(self):
        return "Docset:" + repr(self._docs_list)

    def encode(self):
        """Encode to store compressed inside the database."""
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

        if not self._docs_list:
            return ""
        docs_list = [(k, v) for k, v in self._docs_list.items()]
        docs_list.sort()
        docs = [v[0] for v in docs_list]
        docs_enc = delta_encode(docs)
        # if any score is greater than 255 or lesser than 1, it won't work
        scores = array.array("B", [v[1] for v in docs_list])
        return scores.tobytes() + b"\x00" + docs_enc

    def decode(self, encoded):
        """Decode a compressed docset."""
        def delta_decode(docset, ctor=list, append="append", with_reps=False):
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

        if not encoded or encoded == b"\x00":
            self._docs_list = {}
        else:
            limit = encoded.index(b"\x00")
            docsid = delta_decode(encoded[limit + 1:])
            scores = array.array('B')
            scores.frombytes(encoded[:limit])
            self._docs_list = dict(zip(docsid, scores))


class Union:
    """Class to compute de union of docsets."""
    def __init__(self):
        self.count = None

    def step(self, value):
        other = DocSet(encoded=value)
        if self.count is None:
            self.count = other
        else:
            self.count |= other

    def finalize(self):
        self.count.normalizeValues()
        return self.count.encode()


class Intersect:
    """Class to compute de intersection of docsets."""
    def __init__(self):
        self.count = None

    def step(self, value):
        other = DocSet(encoded=value)
        if self.count is None:
            self.count = other
        else:
            self.count &= other

    def finalize(self):
        self.count.normalizeValues()
        return self.count.encode()


def open_conection(filename):
    """Conects and register data types and aggregate function."""
    # Register the adapter
    adapt_docset = lambda docset: docset.encode()
    sqlite3.register_adapter(DocSet, adapt_docset)

    # Register the converter
    convert_docset = lambda s: DocSet(encoded=s)
    sqlite3.register_converter("docset", convert_docset)

    con = sqlite3.connect(filename, check_same_thread=False,
                          detect_types=sqlite3.PARSE_COLNAMES)
    con.create_aggregate("myintersect", 1, Intersect)
    con.create_aggregate("myunion", 1, Union)
    return con


def to_filename(title):
    """Compute the filename from the title."""
    tt = title.replace(" ", "_")
    tt = tt[0].upper() + tt[1:]
    dir3, arch = to3dirs.get_path_file(tt)
    expected = os.path.join(dir3, arch)
    return expected


class Index(object):
    '''Handles the index.'''

    def __init__(self, directory):
        self._directory = directory
        keyfilename = os.path.join(directory, "index.sqlite")
        self.db = open_conection(keyfilename)
        self.db.executescript('''
            PRAGMA query_only = True;
            PRAGMA journal_mode = MEMORY;
            PRAGMA temp_store = MEMORY;
            PRAGMA synchronous = OFF;
            ''')

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
        """Compute the total number of docs in compressed pages."""
        sql = 'Select pageid, data from docs order by pageid desc limit 1'
        cur = self.db.execute(sql)
        row = cur.fetchone()
        decomp_data = decompress_data(row[1])
        return row[0] * PAGE_SIZE + len(decomp_data)

    def random(self):
        """Returns a random value."""
        docid = random.randint(0, len(self) - 1)
        return self.get_doc(docid)

    def __contains__(self, key):
        """Returns if the key is in the index or not."""
        cur = self.db.execute("SELECT word FROM tokens where word = ?", (key,))
        if cur.fetchone():
            return True
        return False

    @lru_cache(1000)
    def _get_page(self, pageid):
        cur = self.db.execute("SELECT data FROM docs where pageid = ?", (pageid,))
        row = cur.fetchone()
        if row:
            decomp_data = decompress_data(row[0])
            return decomp_data
        return None

    def get_doc(self, docid):
        '''Returns one stored document item.'''
        page_id, rel_id = page_fn(docid)
        data = self._get_page(page_id)
        if data:
            row = data[docid % PAGE_SIZE]
            if not row[0]:
                row[0] = to_filename(row[1])
            return row
        return None

    def _search_asoc_docs(self, keys):
        """Returns all asociated docs ids from a word's set."""
        marks = ', '.join(["?"] * len(keys))
        sql = 'select myintersect(docsets) as "inter [docset]" from tokens'
        sql += f" where word in ({marks})"
        cur = self.db.execute(sql, tuple(keys))
        results = cur.fetchone()
        if not results or not results[0]:
            return DocSet()
        return results[0]

    def search(self, keys):
        """Returns all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        """
        ordered = self._search_asoc_docs(keys)
        for score, ndoc in ordered.tolist():
            dd = self.get_doc(ndoc)
            # dd.append(score)
            yield dd

    def _partial_search(self, key):
        """Returns all the values of a partial key search."""
        sql = 'select myunion(docsets) as "inter [docset]" from tokens'
        sql += f" where word like '%{key}%'"
        cur = self.db.execute(sql)
        results = cur.fetchone()
        # assert keys != ["blanc"]
        if not results or not results[0]:
            return DocSet()
        return results[0]

    def partial_search(self, keys):
        """Returns all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        """
        results = None
        for key in keys:
            if results is None:
                results = self._partial_search(key)
            else:
                results &= self._partial_search(key)
        # assert keys != ["blanc"]
        for score, ndoc in results.tolist():
            dd = self.get_doc(ndoc)
            # dd.append(score)
            yield dd

    @classmethod
    def create(cls, directory, source, show_progress=True):
        """Creates the index in the directory.
        The source must give path, page_score, title and
        a list of extracted words from title in an ordered fashion

        It must return the quantity of pairs indexed.
        """
        import hashlib
        import pickletools
        import timeit

        class ManyInserts():
            def __init__(self, name, sql, buff_size):
                self.sql = sql
                self.name = name
                self.buff_size = buff_size
                self.count = 0
                self.buffer = []

            def append(self, data):
                self.buffer.append(data)
                self.count += 1
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
                logger.info("{:>15}:{}".format(k, v))

        def create_database():
            """Creates de basic structure of new database."""
            script = '''
                PRAGMA JOURNAL_MODE = off;
                PRAGMA synchronous = OFF;
                CREATE TABLE tokens
                    (tokenid INTEGER PRIMARY KEY, word TEXT,
                    results INTEGER, docsets BLOB);
                CREATE TABLE docs (pageid INTEGER PRIMARY KEY, data BLOB);
                '''
            database.executescript(script)

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
                word_scores[word] = word_score
            return word_scores

        def add_docs_keys(source):
            """Add docs and keys registers to db and its rel in memory."""
            idx_dict = {}
            sql = "INSERT INTO docs (pageid, data) VALUES (?, ?)"
            docs_table = Compressed("Documents", sql, PAGE_SIZE)
            allready_seen = set()
            dict_stats["Repeated docs"] = 0
            docid = 0
            for words, page_score, data in source:
                # first insert the new page
                data = list(data)
                if data[0] == to_filename(data[1]):
                    data[0] = None
                # see if the doc is repeated.
                hash_data = hashlib.sha224(pickle.dumps(data)).digest()
                if hash_data not in allready_seen:
                    allready_seen.add(hash_data)
                    data += [page_score]
                    docs_table.append(data)
                    add_words(idx_dict, words, docid, page_score)
                    docid += 1
                else:
                    dict_stats["Repeated docs"] += 1

            docs_table.finish()
            return idx_dict

        def add_words(idx_dict, words, docid, page_score):
            """Stores in a dict the words and its related documents."""
            word_scores = value_words_by_position(words)
            cls.max_page_score = max(cls.max_page_score, page_score)
            for word, word_score in word_scores.items():
                # item_score = max(1, 0.6 * word_score + 0.4 * math.log(page_score))
                cls.max_word_score = max(cls.max_word_score, word_score)
                if word not in idx_dict:
                    idx_dict[word] = DocSet()
                idx_dict[word].append(docid, word_score)

        def add_tokens_to_db(idx_dict):
            """Insert token words in the database."""
            sql_ins = "insert into tokens (tokenid, word, results, docsets) values (?, ?, ?, ?)"
            buffer_t = SQLmany("Tokens", sql_ins, 400)
            logger.debug("Max word score: %r" % cls.max_word_score)
            unit = cls.max_word_score / 255
            # dict_stats["Indexed"] = 0
            for tokenid, (word, docs_list) in enumerate(idx_dict.items()):
                logger.debug("Word: %s %r" % (word, docs_list))
                docs_list.normalizeValues(unit)
                dict_stats["Indexed"] += len(docs_list)
                buffer_t.append((tokenid, word, len(docs_list), docs_list))
            buffer_t.finish()

        def create_indexes():
            script = '''
                create index idx_words on tokens (word, results);
                vacuum;
                '''
            database.executescript(script)

        cls.show_progress = show_progress
        logger.info("Indexing")
        cls.max_word_score = 0
        cls.max_page_score = 0
        initial_time = timeit.default_timer()
        dict_stats = Counter()
        keyfilename = os.path.join(directory, "index.sqlite")
        database = open_conection(keyfilename)
        create_database()
        idx_dict = add_docs_keys(source)
        add_tokens_to_db(idx_dict)
        create_indexes()
        dict_stats["Total time"] = int(timeit.default_timer() - initial_time)
        dict_stats["Max word score"] = cls.max_word_score
        dict_stats["Max page score"] = cls.max_page_score
        show_stats()
        return dict_stats["Indexed"]
