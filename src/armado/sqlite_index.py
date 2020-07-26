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


import array
import logging
import os
import pickle
import random
import sqlite3
import hashlib
import zlib as best_compressor  # zlib is faster, lzma has better ratio.
from collections import defaultdict
from functools import lru_cache

from src.armado import to3dirs

logger = logging.getLogger(__name__)

MAX_IDX_FIELDS = 8
PAGE_SIZE = 1024


def decompress_data(data):
    return pickle.loads(best_compressor.decompress(data))


class DocSet:
    """Data type to encode, decode & compute documents-id's sets."""
    def __init__(self, encoded=None):
        self._docs_list = {}
        if encoded:
            self._docs_list = DocSet.decode(encoded)

    def append(self, docid, score):
        """Append an item to the docs_list."""
        self._docs_list[docid] = self._docs_list.get(docid, 0) + score

    def normalize_values(self, unit=None):
        """Divide every doc score to avoid large numbers."""
        if not self._docs_list:
            return
        if not unit:
            unit = max(list(self._docs_list.values())) / 255
        # Cannot raise values, only lower them
        if unit >= 1:
            for k, v in self._docs_list.items():
                self._docs_list[k] = int(v / unit)
        for k, v in self._docs_list.items():
            self._docs_list[k] = max(1, min(255, v))

    def tolist(self):
        """Returns a sorted list of docs, by value."""
        to_list = [(v, k) for k, v in self._docs_list.items()]
        to_list.sort(reverse=True)
        return to_list

    def __ior__(self, other):
        """Union and add value to other docset."""
        for key, value in other._docs_list.items():
            self._docs_list[key] = self._docs_list.get(key, 0) + value
        return self

    def __iand__(self, other):
        """Intersect and add value to other docset."""
        common = set(self._docs_list) & set(other._docs_list)
        self._docs_list = {k: self._docs_list[k] + other._docs_list[k] for k in common}
        return self

    def __len__(self):
        return len(self._docs_list)

    def __repr__(self):
        return "Docset:" + repr(self._docs_list)

    @staticmethod
    def delta_encode(ordered):
        """Compress an array of numbers into a bytes object."""
        result = array.array('B')
        add_to_result = result.append

        prev_doc = 0
        for doc in ordered:
            doc, prev_doc = doc - prev_doc, doc
            while True:
                b = doc & 0x7F
                doc >>= 7
                if doc:
                    # the number is not exhausted yet,
                    # store these 7b with the flag and continue
                    add_to_result(b | 0x80)
                else:
                    # we're done, store the remaining bits
                    add_to_result(b)
                    break

        return result.tobytes()

    @staticmethod
    def delta_decode(ordered):
        """Decode a compressed encoded bucket.

        - ordered is a bytes object, representing a byte's array
        - ctor is the final container
        - append is the callable attribute used to add an element into the ctor
        """
        result = []
        add_to_result = result.append

        prev_doc = doc = shift = 0

        for b in ordered:
            doc |= (b & 0x7F) << shift
            shift += 7

            if not (b & 0x80):
                # the sequence ended
                prev_doc += doc
                add_to_result(prev_doc)
                doc = shift = 0

        return result

    def encode(self):
        """Encode to store compressed inside the database."""
        if not self._docs_list:
            return ""
        docs_list = [(k, v) for k, v in self._docs_list.items()]
        docs_list.sort()
        docs = [v[0] for v in docs_list]
        docs_enc = DocSet.delta_encode(docs)
        # if any score is greater than 255 or lesser than 1, it won't work
        scores = array.array("B", [v[1] for v in docs_list])
        return scores.tobytes() + b"\x00" + docs_enc

    @staticmethod
    def decode(encoded):
        """Decode a compressed docset."""
        if not encoded or encoded == b"\x00":
            docs_list = {}
        else:
            limit = encoded.index(b"\x00")
            docsid = DocSet.delta_decode(encoded[limit + 1:])
            scores = array.array('B')
            scores.frombytes(encoded[:limit])
            docs_list = dict(zip(docsid, scores))
        return docs_list


def open_connection(filename):
    """Connect and register data types and aggregate function."""
    # Register the adapter
    def adapt_docset(docset):
        return docset.encode()
    sqlite3.register_adapter(DocSet, adapt_docset)

    # Register the converter
    def convert_docset(s):
        return DocSet(encoded=s)
    sqlite3.register_converter("docset", convert_docset)

    con = sqlite3.connect(filename, check_same_thread=False,
                          detect_types=sqlite3.PARSE_COLNAMES)
    return con


def to_filename(title):
    """Compute the filename from the title."""
    if not title:
        return title
    tt = title.replace(" ", "_")
    if len(tt) >= 2:
        tt = tt[0].upper() + tt[1:]
    elif len(tt) == 1:
        tt = tt[0].upper()

    dir3, arch = to3dirs.get_path_file(tt)
    expected = os.path.join(dir3, arch)
    return expected


class Index(object):
    """Handle the index."""

    def __init__(self, directory):
        self._directory = directory
        keyfilename = os.path.join(directory, "index.sqlite")
        self.db = open_connection(keyfilename)
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
            docset = self._search_asoc_docs(key)
            yield key, docset

    def values(self):
        '''Returns an iterator over the stored values.'''
        cur = self.db.execute("SELECT pageid, data FROM docs ORDER BY pageid")
        for row in cur.fetchall():
            decomp_data = decompress_data(row[1])
            for doc in decomp_data:
                yield doc

    @lru_cache(1)
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
        page_id, rel_position = divmod(docid, PAGE_SIZE)
        data = self._get_page(page_id)
        if not data:
            return None
        row = data[rel_position]
        # if the html filename is marked as computable
        # do it and store in position 0.
        if row[0] is None:
            row[0] = to_filename(row[1])
        return row

    def _search_asoc_docs(self, keys):
        """Returns all asociated docs ids from a word's set."""
        if not keys:
            return DocSet()
        marks = ', '.join(["?"] * len(keys))
        sql = "select docsets as 'ds [docset]' from tokens"
        sql += " where word in ({})".format(marks)
        cur = self.db.execute(sql, tuple(keys))
        row = cur.fetchone()
        if not row:
            return DocSet()
        results = row[0]
        for row in cur.fetchall():
            results &= row[0]
        return results

    def search(self, keys):
        """Returns all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        """
        docset = self._search_asoc_docs(keys)
        for score, ndoc in docset.tolist():
            doc_data = self.get_doc(ndoc)
            yield doc_data

    def _partial_search(self, key):
        """Returns all the values of a partial key search."""
        sql = 'select docsets as "ds [docset]" from tokens'
        sql += " where word like '%{}%'".format(key)
        cur = self.db.execute(sql)
        row = cur.fetchone()
        if not row:
            return DocSet()
        results = row[0]
        for row in cur.fetchall():
            results |= row[0]
        return results

    def partial_search(self, keys):
        """Returns all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        """
        if not keys:
            return None
        results = self._partial_search(keys[0])
        for key in keys[1:]:
            results &= self._partial_search(key)
        # assert keys != ["blanc"]
        for score, ndoc in results.tolist():
            doc_data = self.get_doc(ndoc)
            yield doc_data

    @classmethod
    def create(cls, directory, source, show_progress=True):
        """Creates the index in the directory.
        The source must give path, page_score, title and
        a list of extracted words from title in an ordered fashion

        It must return the quantity of pairs indexed.
        """
        import pickletools
        import timeit

        class SQLmany:
            """Execute many INSERTs greatly improves the performance."""
            def __init__(self, name, sql):
                self.sql = sql
                self.name = name
                self.count = 0
                self.buffer = []

            def append(self, data):
                """Append one data set to persist on db."""
                self.buffer.append(data)
                self.count += 1
                if self.count % PAGE_SIZE == 0:
                    self.persist()
                    self.buffer = []
                if cls.show_progress and self.count % 1000 == 0:
                    print(".", end="", flush=True)
                return self.count - 1

            def finish(self):
                """Finish the process and prints some data."""
                if self.buffer:
                    self.persist()
                if cls.show_progress:
                    print(self.name, ":", self.count, flush=True)
                dict_stats[self.name] = self.count

            def persist(self):
                """Commit data to index."""
                database.executemany(self.sql, self.buffer)
                database.commit()

        class Compressed(SQLmany):
            """Creates the table of compressed documents information.

            The groups is PAGE_SIZE lenght, pickled and compressed."""
            def persist(self):
                """Compress and commit data to index."""
                pickdata = pickletools.optimize(pickle.dumps(self.buffer))
                comp_data = best_compressor.compress(pickdata)
                page_id = (self.count - 1) // PAGE_SIZE
                database.execute(self.sql, (page_id, comp_data))
                database.commit()

        def create_database():
            """Creates de basic structure of new database."""
            script = '''
                PRAGMA journal_mode = OFF;
                PRAGMA synchronous = OFF;
                CREATE TABLE tokens
                    (word TEXT,
                    results INTEGER,
                    docsets BLOB);
                CREATE TABLE docs
                    (pageid INTEGER PRIMARY KEY,
                    data BLOB);
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
            idx_dict = defaultdict(DocSet)
            sql = "INSERT INTO docs (pageid, data) VALUES (?, ?)"
            docs_table = Compressed("Documents", sql)
            allready_seen = set()
            dict_stats["Repeated docs"] = 0
            for words, page_score, data in source:
                # first insert the new page
                # see if the doc is repeated.
                # the 1 position stores title, so use it.
                # hash_data = (data[1].__hash__(), data.__hash__())
                hash_data = hashlib.sha224(pickle.dumps(data)).digest()
                if hash_data not in allready_seen:
                    allready_seen.add(hash_data)
                    data = list(data)
                    # see if html file name can be deduced
                    # from the title. Mark using None
                    if data[0] == to_filename(data[1]):
                        data[0] = None
                    data += [page_score]
                    docid = docs_table.append(data)
                    add_words(idx_dict, words, docid, page_score)
                else:
                    print("!", end="")
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
                idx_dict[word].append(docid, word_score)

        def add_tokens_to_db(idx_dict):
            """Insert token words in the database."""
            sql_ins = "insert into tokens (word, results, docsets) values (?, ?, ?)"
            token_store = SQLmany("Tokens", sql_ins)
            logger.debug("Max word score: %r" % cls.max_word_score)
            unit = cls.max_word_score / 255
            for word, docs_list in idx_dict.items():
                logger.debug("Word: %s %r" % (word, docs_list))
                docs_list.normalize_values(unit)
                dict_stats["Indexed"] += len(docs_list)
                token_store.append((word, len(docs_list), docs_list))
            token_store.finish()

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
        dict_stats = defaultdict(int)
        keyfilename = os.path.join(directory, "index.sqlite")
        database = open_connection(keyfilename)
        create_database()
        idx_dict = add_docs_keys(source)
        add_tokens_to_db(idx_dict)
        create_indexes()
        dict_stats["Total time"] = int(timeit.default_timer() - initial_time)
        dict_stats["Max word score"] = cls.max_word_score
        dict_stats["Max page score"] = cls.max_page_score
        # Finally, show some statistics.
        for k, v in dict_stats.items():
            logger.info("{:>15}:{}".format(k, v))
        return dict_stats["Indexed"]
