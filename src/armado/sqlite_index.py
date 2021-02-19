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
import math
import operator
import os
import pickle
import random
import unicodedata
import sqlite3
from collections import defaultdict
from functools import lru_cache
import lzma as best_compressor  # zlib is faster, lzma has better ratio.

from src.armado import to3dirs

logger = logging.getLogger(__name__)

PAGE_SIZE = 512
MAX_RESULTS = 500


class IndexEntry:
    """Article or redir index entry data structure."""

    __slots__ = ('rtype', 'link', 'title', 'score', 'description', 'subtitle')

    # types of records
    TYPE_ORIG_ARTICLE = 0  # original article (may be target of possible redirects)
    TYPE_ORIG_SIMPLE_LINK = 1  # original article whose link can be calculated from the title
    TYPE_REDIRECT = 2  # a redirect to some original title

    def __init__(self, rtype, link, title, score=0, description="", subtitle=""):
        self.rtype = rtype
        self.link = link
        self.title = title
        self.score = score
        self.description = description
        self.subtitle = subtitle

    def __repr__(self):
        values = ["{}:{!r}".format(attr, getattr(self, attr)) for attr in self.__slots__]
        return 'IndexEntry: ' + ','.join(values)

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr) for attr in self.__slots__)

    def __hash__(self):
        return hash(tuple(getattr(self, attr) for attr in self.__slots__))


# cache for normalized chars
_normalized_chars = {}


def normalize_words(txt):
    """Normalize every word from a sentence.

    - remove all diacritical marks
    - convert all letters to lowercase
    - keep non-ascii chars to support non-latin alphabets
    """
    # decompose unicode chars
    txt = unicodedata.normalize('NFKD', txt)

    # construct normalized text
    txt_norm = []
    for c in txt:
        try:
            c_norm = _normalized_chars[c]
        except KeyError:
            c_norm = '' if unicodedata.combining(c) else c.lower()
            _normalized_chars[c] = c_norm
        txt_norm.append(c_norm)

    return ''.join(txt_norm)


def decompress_data(data):
    return pickle.loads(best_compressor.decompress(data))


class DocSet:
    """Data type to encode, decode & compute documents-id's sets."""
    SEPARATOR = 0xFF

    def __init__(self):
        self._docs_list = defaultdict(list)
        self.items = self._docs_list.items

    def append(self, docid, position):
        """Append an item to the docs_list."""
        self._docs_list[docid].append(position)

    def __len__(self):
        return len(self._docs_list)

    def __repr__(self):
        value = repr(self._docs_list).replace("[", "").replace("],", "|").replace("]})", "}")
        curly = value.index("{")
        value = value[curly:curly + 75]
        if not value.endswith("}"):
            value += " ..."
        return "<Docset: len={} {}>".format(len(self._docs_list), value)

    def __eq__(self, other):
        return self._docs_list == other._docs_list

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
        docs_list = []
        for key, values in self._docs_list.items():
            docs_list.extend((key, value) for value in values)
        docs_list.sort()
        docs = [v[0] for v in docs_list]
        docs_enc = DocSet.delta_encode(docs)
        # if any score is greater than 255 or lesser than 1, it won't work
        position = [v[1] for v in docs_list]
        if any([x >= self.SEPARATOR for x in position]):
            raise ValueError("Positions can't be greater than 254.")
        position.append(self.SEPARATOR)
        position = array.array("B", position)
        return position.tobytes() + docs_enc

    @classmethod
    def decode(cls, encoded):
        """Decode a compressed docset."""
        docset = cls()
        if len(encoded) > 1:
            limit = encoded.index(cls.SEPARATOR)
            docsid = cls.delta_decode(encoded[limit + 1:])
            positions = array.array('B')
            positions.frombytes(encoded[:limit])
            for docid, position in zip(docsid, positions):
                docset._docs_list[docid].append(position)
        return docset


def open_connection(filename):
    """Connect and register data types and aggregate function."""
    # Register the adapter
    def adapt_docset(docset):
        return docset.encode()
    sqlite3.register_adapter(DocSet, adapt_docset)

    # Register the converter
    def convert_docset(s):
        return DocSet.decode(s)
    sqlite3.register_converter("docset", convert_docset)

    con = sqlite3.connect(filename, check_same_thread=False, detect_types=sqlite3.PARSE_COLNAMES)
    return con


def to_filename(title):
    """Compute the filename from the title."""
    tt = title.replace(" ", "_")
    if len(tt) >= 2:
        tt = tt[0].upper() + tt[1:]
    elif len(tt) == 1:
        tt = tt[0].upper()
    else:
        raise ValueError("Title must have at least one character")

    dir3, arch = to3dirs.get_path_file(tt)
    expected = os.path.join(dir3, arch)
    return expected


class Search:
    """Fetch and order some search."""
    def __init__(self, db, keys):
        self.db = db
        self.docs = defaultdict(dict)
        self.keys = keys
        # create a set of result w/all keys
        results = self._get_docs(keys[0])
        for key in keys[1:]:
            results &= self._get_docs(key)

        # computes the similitude of phrase
        self.ordered = []
        for docid in results:
            word_quant = self._get_doc_word_quant(docid)
            phrase = [""] * word_quant
            for pos, word in self.docs[docid].items():
                phrase[pos] = word
            similitude = self.iterative_levenshtein(phrase)

            # first docid are a LOT more important
            order_factor = int(40000 * math.pow(docid + 1, -.5))

            self.ordered.append((order_factor - similitude, docid))

        self.ordered.sort(reverse=True)

    @lru_cache(1000)
    def _get_page(self, pageid):
        """Return the array of word_quants in word of a page's titles."""
        cur = self.db.execute("SELECT word_quants FROM docs where pageid = ?", (pageid,))
        row = cur.fetchone()
        decomp_data = array.array("B")
        if row:
            decomp_data.frombytes(row[0])
        return decomp_data

    def _get_doc_word_quant(self, docid):
        """Return one stored document item."""
        page_id, rel_position = divmod(docid, PAGE_SIZE)
        word_quants = self._get_page(page_id)
        if not word_quants:
            raise ValueError("Inconsistency on data, docid non exists")
        return word_quants[rel_position]

    def _get_docs(self, key):
        """Store the words asoc w/ the docs & return a found docs's set."""
        found = set()
        for word, docset in self._fetch(key):
            for docid, positions in docset.items():
                for pos in positions:
                    self.docs[docid][pos] = word
                found.add(docid)
        return found

    def _fetch(self, key):
        """Return all the values of a partial key search."""
        sql = "select word, docsets as 'ds [docset]' from tokens"
        sql += " where word like '%{}%'".format(key)
        cur = self.db.execute(sql)
        for row in cur.fetchall():
            yield row[0], row[1]

    def iterative_levenshtein(self, phrase):
        """Compute the Levenshtein distance between the lists keys and phrase.

        For all i and j, dist[i,j] will contain the Levenshtein
        distance between the first i items of keys and the
        first j items of phrase
        """

        # If there are exact match, put on the top
        if self.keys == phrase:
            return -1000

        keys = self.keys
        rows = len(keys) + 1
        cols = len(phrase) + 1
        deletes, inserts, substitutes = 200, 25, 30

        dist = [[0 for c in range(cols)] for r in range(rows)]

        # source prefixes can be transformed into empty strings
        # by deletions:
        for row in range(1, rows):
            dist[row][0] = row * deletes

        # target prefixes can be created from an empty source string
        # by inserting the characters.
        # Inserts in the last positions cost more.
        for col in range(1, cols):
            dist[0][col] = int(col * inserts ** 1.2)

        for row in range(1, rows):
            lenkey = len(keys[row - 1])

            for col in range(1, cols):
                lendiff = len(phrase[col - 1]) - lenkey
                if keys[row - 1] == phrase[col - 1]:
                    cost = 0  # if equal, no subtituion cost
                elif phrase[col - 1].startswith(keys[row - 1]):
                    # if starts with key, just half cost
                    cost = lendiff * (substitutes // 2)
                elif keys[row - 1] in phrase[col - 1]:
                    # if includes the key, multiply
                    cost = lendiff * substitutes
                else:
                    # total substitution, cost by sum of lengths
                    lendiff += 2 * lenkey
                    cost = substitutes * lendiff

                dist[row][col] = min(dist[row - 1][col] + deletes,
                                     dist[row][col - 1] + inserts,
                                     dist[row - 1][col - 1] + cost)  # substitution

        return dist[row][col]


class Index:
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
        """Return an iterator over the stored keys."""
        cur = self.db.execute("SELECT word FROM tokens")
        for row in cur.fetchall():
            yield row[0]

    def items(self):
        """Return an iterator over the stored items."""
        sql = "select word, docsets as 'ds [docset]' from tokens"
        cur = self.db.execute(sql)
        for row in cur.fetchall():
            yield row[0], row[1]

    def values(self):
        """Return an iterator over the stored values."""
        cur = self.db.execute("SELECT pageid, data FROM docs ORDER BY pageid")
        for row in cur.fetchall():
            decomp_data = decompress_data(row[1])
            for doc in decomp_data:
                yield doc

    @lru_cache(1)
    def __len__(self):
        """Compute the total number of docs in compressed pages."""
        sql = "Select pageid, data from docs order by pageid desc limit 1"
        cur = self.db.execute(sql)
        row = cur.fetchone()
        decomp_data = decompress_data(row[1])
        return row[0] * PAGE_SIZE + len(decomp_data)

    def random(self):
        """Return a random value."""
        docid = random.randint(0, len(self) - 1)
        return self.get_doc(docid)

    def __contains__(self, key):
        """Return if the key is in the index or not."""
        cur = self.db.execute("SELECT word FROM tokens where word = ?", (key,))
        if cur.fetchone():
            return True
        return False

    @lru_cache(1000)
    def _get_page(self, pageid):
        """Get a page of doc entry data."""
        cur = self.db.execute("SELECT data FROM docs where pageid = ?", (pageid,))
        row = cur.fetchone()
        if row:
            decomp_data = decompress_data(row[0])
            return decomp_data
        return None

    def get_doc(self, docid):
        """Return one stored document item."""
        page_id, rel_position = divmod(docid, PAGE_SIZE)
        data = self._get_page(page_id)
        if not data:
            raise IndexError("Non existing docid")
        idx_entry = data[rel_position]
        # if the html filename is marked as computable
        # do it and store in position 0.
        # idx_entry = Indexentry(*row)
        if idx_entry.link is None:
            idx_entry.link = to_filename(idx_entry.title)
        return idx_entry

    def search(self, keys):
        """Return all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        """
        keys = list(map(normalize_words, keys))
        files_yielded = set()
        docset = Search(self.db, keys)
        for score, ndoc in docset.ordered:
            doc_data = self.get_doc(ndoc)
            # Do not return more than one index result to the same file.
            if doc_data.link not in files_yielded:
                files_yielded.add(doc_data.link)
                yield doc_data
            if len(files_yielded) >= MAX_RESULTS:
                break

    @classmethod
    def create(cls, directory, source):
        """Create the index in the directory.

        The source must give path, page_score, title and
        a list of extracted words from title in an ordered fashion
        It must return the quantity of pairs indexed.
        """
        import pickletools
        import time
        from progress.bar import Bar

        class SQLmany:
            """Execute many INSERTs greatly improves the performance."""
            def __init__(self, name, sql, quantity):
                self.sql = sql
                self.name = name
                self.count = 0
                self.buffer = []
                self.progress_bar = Bar(name, max=quantity)

            def append(self, data):
                """Append one data set to persist on db."""
                self.buffer.append(data)
                self.count += 1
                if self.count % PAGE_SIZE == 0:
                    self.persist()
                    self.buffer = []
                # self.count is the quantity of docs added
                # but it is the index that is returned
                # and it is zero based, hence one less.
                self.progress_bar.next()
                return self.count - 1

            def finish(self):
                """Finish the process and show some data."""
                if self.buffer:
                    self.persist()
                self.progress_bar.finish()
                dict_stats[self.name] = self.count

            def persist(self):
                """Commit data to index."""
                database.executemany(self.sql, self.buffer)
                database.commit()

        class Compressed(SQLmany):
            """Creates the table of compressed documents information.

            The groups is PAGE_SIZE word_quant, pickled and compressed."""
            def persist(self):
                """Compress and commit data to index."""
                docs_data = []
                word_quants = array.array("B")
                for word_quant, data in self.buffer:
                    word_quants.append(word_quant)
                    docs_data.append(data)
                pickdata = pickletools.optimize(pickle.dumps(docs_data))
                comp_data = best_compressor.compress(pickdata)
                page_id = (self.count - 1) // PAGE_SIZE
                database.execute(self.sql, (page_id, word_quants.tobytes(), comp_data))
                database.commit()

        def create_database():
            """Creates de basic structure of new database."""
            script = """
                PRAGMA journal_mode = OFF;
                PRAGMA synchronous = OFF;
                CREATE TABLE tokens
                    (word TEXT,
                    docsets BLOB);
                CREATE TABLE docs
                    (pageid INTEGER PRIMARY KEY,
                    word_quants BLOB,
                    data BLOB);
                """

            database.executescript(script)

        def add_docs_keys(source):
            """Add docs and keys registers to db and its rel in memory."""
            idx_dict = defaultdict(DocSet)
            sql = "INSERT INTO docs (pageid, word_quants, data) VALUES (?, ?, ?)"
            docs_table = Compressed("Documents", sql, len(source))

            for words, page_score, idx_entry in source:
                if idx_entry.link == to_filename(idx_entry.title):
                    idx_entry.link = None
                    idx_entry.rtype = IndexEntry.TYPE_ORIG_SIMPLE_LINK
                docid = docs_table.append((len(words), idx_entry))
                for idx, word in enumerate(words):
                    idx_dict[word].append(docid, idx)

            docs_table.finish()
            return idx_dict

        def add_tokens_to_db(idx_dict):
            """Insert token words in the database."""
            sql_ins = "insert into tokens (word, docsets) values (?, ?)"
            token_store = SQLmany("Tokens", sql_ins, len(idx_dict))
            for word, docs_list in idx_dict.items():
                logger.debug("Word: %s %r" % (word, docs_list))
                dict_stats["Indexed"] += len(docs_list)
                token_store.append((word, docs_list))
            token_store.finish()

        def create_indexes():
            script = '''
                create index idx_words on tokens (word);
                vacuum;
                '''
            database.executescript(script)

        logger.info("Indexing")
        initial_time = time.time()
        dict_stats = defaultdict(int)
        keyfilename = os.path.join(directory, "index.sqlite")
        database = open_connection(keyfilename)
        create_database()
        ordered_source = sorted(source, reverse=True, key=operator.itemgetter(1))
        if not ordered_source:
            raise ValueError("No data to index")
        idx_dict = add_docs_keys(ordered_source)
        add_tokens_to_db(idx_dict)
        create_indexes()
        dict_stats["Total time"] = int(time.time() - initial_time)
        # Finally, show some statistics.
        for k, v in dict_stats.items():
            logger.info("{:>20}:{}".format(k, v))
        return dict_stats["Indexed"]
