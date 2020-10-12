# Copyright 2014-2020 CDPedistas (see AUTHORS.txt)
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
import bisect
import operator
import os
import pickle
import random
import sys
import logging
from functools import lru_cache
from lzma import LZMAFile as CompressedFile

DOCSTORE_BUCKET_SIZE = 1 << 20
DOCSTORE_CACHE_SIZE = 20

logger = logging.getLogger(__name__)


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


delta_encode_str = delta_encode
delta_decode_str = delta_decode


class FrozenStringList:
    """Manage a FrozenStringList.

    - self.heap contains a concatenation of every string appended.
    - self.index is an array of long bytes and represents the begin position
      of every substring added to heap.
    """
    def __init__(self, iterable=None):
        self.index = array.array('l', [0])
        self.heap = b""
        if iterable:
            self.extend(iterable)

    def __getitem__(self, ix):
        if ix < 0:
            raise IndexError("Negative index")
        elif ix >= (len(self.index) - 1):
            raise IndexError("FrozenStringList index out of range")
        else:
            index = self.index
            return self.heap[index[ix]:index[ix + 1]]

    def __len__(self):
        return len(self.index) - 1

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, list(self))

    def append(self, value):
        """Append one term to the frozenlist."""
        if not isinstance(value, bytes):
            raise TypeError("Bytes expected")

        self.index.append(len(self.heap) + len(value))
        self.heap += value

    def extend(self, iterable):
        """Extends the list.

        self.heap contain a concatenation of every string appended
        self.index is an array of long bytes and represents the begin position
        of every substring added to heap.
        """
        iterable = list(iterable)
        len_ = len

        pos = len_(self.heap)
        index_a = self.index.append
        for s in iterable:
            pos += len_(s)
            index_a(pos)
        self.heap += b''.join(iterable)

    def pickle(self):
        encoded_index = delta_encode_str(self.index, sorted=lambda x: x, with_reps=True)
        return encoded_index, self.heap

    @staticmethod
    def unpickle(data):
        rv = FrozenStringList()
        rv.index = delta_decode_str(
            data[0], ctor=(lambda: array.array('l')), append='append', with_reps=True
        )
        rv.heap = data[1]
        return rv


class TermSimilitudeMatrixBase:
    """Find similar terms to the one searched.

    Includes 2 data structures, both FrozenStringList.
    - self.terms is used to store the alphabetically ordered terms index.
    - self.matrix is a square matrix and have has many rows and columns as
      terms are indexed. A cell can be true, meaning that both terms
      (the one of the row and the one of the column) are similar.
    In order to provide a compressed storage use, every row is delta_encoded,
    and every delta_encoded row is added to a FrozenStringList.
    """

    def __init__(self, terms=[], progress_callback=lambda: None):
        self.terms = terms = FrozenStringList(sorted(terms))
        self.matrix = matrix = FrozenStringList()

        if terms:
            similar = self.similar_impl
            self.init_similar_impl()
            matrix_a = matrix.append

            N = len(terms)
            for i, t1 in enumerate(terms):
                bucket = array.array('l')
                bucket_a = bucket.append
                valid = not t1  # <- it's ok for empty terms not to match themselves
                for i2 in similar(t1):
                    if i != i2:  # <- omit the diagonal, which is implicit
                        bucket_a(i2)
                    else:
                        valid = True
                assert valid, ("Invalid bucket - the term must match to itself", t1)
                matrix_a(delta_encode_str(bucket))

                if not (i % 100):
                    progress_callback(i * 100.0 / N)

    def init_similar_impl(self):
        """Initilize similarity data structure.

        To initialize something for 'similar', inherit this
        class function. It is called BEFORE calling similar.
        The terms are stored in self.terms, ordered by ids.
        """
        pass

    def similar_impl(self, t):
        """Iterable using t's similar terms indices."""
        raise NotImplementedError

    def pickle(self):
        return (self.terms.pickle(), self.matrix.pickle())

    @staticmethod
    def unpickle(data):
        rv = TermSimilitudeMatrixBase()
        rv.terms = FrozenStringList.unpickle(data[0])
        rv.matrix = FrozenStringList.unpickle(data[1])
        assert len(rv.terms) == len(rv.matrix), ("Invalid pickle", rv.terms, rv.matrix)
        return rv

    def lookup_term_index(self, t):
        """Return the index for the specified term."""
        i = bisect.bisect_left(self.terms, t)
        if i >= len(self.terms) or self.terms[i] != t:
            raise KeyError(t)

        return i

    def lookup_term_value(self, i):
        """Return the text for the specified term index.

        Raises IndexError if the index is invalid.
        """
        return self.terms[i]

    def contains_term(self, t):
        try:
            self.lookup_term_index(t)
            return True
        except KeyError:
            return False

    def similar_terms(self, t):
        """Return an iterable over the indices of similar terms.

        Raises KeyError if the term is not found.
        """
        terms = self.terms

        if not terms:
            return

        #
        # Look up substrings of the term, starting from
        # less likely / most restricting downwards to
        # most likely / less restrincing ones.
        #
        # It's quadratic on the length of the term,
        # so we'll limit the length of the subterm to 20 characters max
        #
        iterator = iter(
            t[a:a + length]
            for length in range(min(20, len(t)), 0, -1)
            for a in range(len(t) - length + 1)
        )
        for tv in iterator:
            try:
                # an exact match is a godsend - we just look it up
                i = self.lookup_term_index(tv)
            except KeyError:
                i = None

            if i is not None:
                candidates = delta_decode_str(self.matrix[i])
                candidates.add(i)  # <- the matrix omits the diagnoal
                break
        else:
            # ouch... no substring found in the matrix.
            # We must do things the slow way then...
            # NOTE: this should be most unlikely, since most alphabet
            #   letters should be in the index and thus in the matrix.
            candidates = set()
            candidates_a = candidates.add
            for i, st in enumerate(terms):
                if st in t:
                    # Found a substring in the matrix, all matches
                    # will be a subset of matches for the substring
                    candidates = delta_decode_str(self.matrix[i])
                    candidates.add(i)  # <- the matrix omits the diagnoal
                    break
                elif t in st:
                    candidates_a(i)
            else:
                # don't recheck candidates if we did a full scan
                for i in candidates:
                    yield i
                return

        # it may be a partial match - we must filter mismatches
        for i in candidates:
            if t in terms[i]:
                yield i


try:
    import SuffixTree

    class TermSimilitudeMatrix(TermSimilitudeMatrixBase):
        """Uses SuffixTree library compiled in C++."""
        def init_similar_impl(self):
            self.stree = stree = SuffixTree.SubstringDict()
            for i, t in enumerate(self.terms):
                stree[t] = i

        def similar_impl(self, t):
            """Return the set of similar terms."""
            # SuffixTree tiende a generar muchas repeticiones
            return set(self.stree[t])


except ImportError:

    class TermSimilitudeMatrix(TermSimilitudeMatrixBase):
        """Pure python implementation.

        Uses a simplified condition, term t is included in other,
        is yielded as similar.
        """
        def similar_impl(self, t):
            """Return the set of similar terms."""
            for i, st in enumerate(self.terms):
                if t in st:
                    yield i


class Index(object):
    """Handle the index.

    It's the class that implements the index's API.
    Main functions are:
    - create: to create the index data structure
    - search and partial_search: to find any terms
    - random: returns a random entry
    """

    def __init__(self, directory):
        self._directory = directory

        # open the key shelve
        # Format:
        #   ( matrix, docsets )
        #   matrix = TermSimilitudeMatrix
        #   docsets = FrozenStringList
        keyfilename = os.path.join(directory, "compindex.key.xz")
        fh = CompressedFile(keyfilename, "rb")

        # TODO: research and document why the encoding here is latin-1
        matrix, docsets = pickle.load(fh, encoding='latin-1')
        fh.close()

        matrix = TermSimilitudeMatrix.unpickle(matrix)
        docsets = FrozenStringList.unpickle(docsets)

        self.matrix, self.docsets = matrix, docsets

        # see how many id files we have
        filenames = []
        for fn in os.listdir(directory):
            if fn.startswith("compindex-") and fn.endswith(".ids.xz"):
                filenames.append(fn)
        self.idfiles_count = len(filenames)

    @lru_cache(DOCSTORE_CACHE_SIZE)
    def _get_ids_shelve(self, cual):
        """Return the ids index."""
        fname = os.path.join(self._directory, "compindex-%02d.ids.xz" % cual)
        fh = CompressedFile(fname, "rb")
        idx = pickle.load(fh)
        fh.close()
        return idx

    def _get_info_id(self, allids):
        """Return the values for the given ids.

        As it groups the ids according to the file, is much faster than
        retrieving one by one.
        """
        # group the id per file
        cuales = {}
        cualesg = cuales.get
        ocual = bucket = None
        idfiles_count = self.idfiles_count
        for i in allids:
            cual = i % idfiles_count
            if cual != ocual:
                # only look it up if it's different
                # than the last - this saves a lot of lookups
                bucket = cualesg(cual)
                if bucket is None:
                    bucket = cuales[cual] = []
                bucket = bucket.append
            bucket(i)

        # get the info for each file
        for cual, ids in cuales.items():
            idx = self._get_ids_shelve(cual)
            for i in ids:
                yield idx[i]

    def items(self):
        """Return an iterator over the stored items."""
        matrix = self.matrix
        doc_lookup = self._get_info_id
        for i, docset in enumerate(self.docsets):
            key = matrix.lookup_term_value(i).decode("utf8")
            values = doc_lookup(delta_decode(docset))
            yield key, list(values)

    def values(self):
        """Return an iterator over the stored values."""
        doc_lookup = self._get_info_id
        res = set()
        for i, docset in enumerate(self.docsets):
            res |= delta_decode(docset)
        values = doc_lookup(res)
        for v in values:
            yield v

    def keys(self):
        return [k.decode("utf8") for k in self.matrix.terms]

    def random(self):
        """Return a random value."""
        cual = random.randint(0, self.idfiles_count - 1)
        idx = self._get_ids_shelve(cual)
        return random.choice(list(idx.values()))

    def __contains__(self, key):
        """Return if the key is in the index or not."""
        return self.matrix.contains_term(key.encode("utf8"))

    def search(self, keys):
        """Return all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        """
        results = None
        matrix = self.matrix
        docsets = self.docsets
        for key in keys:
            key = key.encode("utf8")
            if not matrix.contains_term(key):
                continue
            # returns a set of matches
            allids = delta_decode(docsets[matrix.lookup_term_index(key)])
            if results is None:
                results = allids
            else:
                # this and is the intersection of both sets
                results &= allids

        if not results:
            return []

        # do AND between results, and get the values from ids
        return self._get_info_id(results)

    def partial_search(self, keys):
        """Return all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        """
        results = None
        matrix = self.matrix
        docsets = self.docsets
        for key_search in keys:
            key_search = key_search.encode("utf8")

            # the partial result starts with an empty set, that will be
            # filled in the OR reduce
            partial_res = set()

            # search in all the keys, for partial match
            for key_stored in matrix.similar_terms(key_search):
                partial_res |= delta_decode(docsets[key_stored])

            # all partial results are reduced with AND
            if results is None:
                results = partial_res
            else:
                results &= partial_res

        if not results:
            return []

        # do AND between results, and get the values from ids
        return self._get_info_id(results)

    @classmethod
    def create(cls, directory, source):
        """Create the index in the directory.

        The "source" generates pairs (key, value) to store in the index.  The
        key must be a string, the value can be any hashable Python object.

        It must return the numbers of pairs indexed.
        """
        # dict container of the values of every doc numbered. Keys are integers
        ids_shelf = {}
        # contains 'buckets' (arrays of integers) associated with every key (word)
        key_shelf = {}
        # ids counter
        ids_cnter = 0
        #  indexed entries's counter
        indexed_counter = 0

        # fill them
        # key are words extracted from titles, redirects
        # value are tuples (nomhtml, titulo, score, its_a_title, primtexto)
        for keys, score, data in source:
            checkme = all([isinstance(keys, list),
                          isinstance(score, int),
                          isinstance(data, tuple)])
            if not checkme:
                raise TypeError("The keys and value must be lists, score must be integer")
            if not all([isinstance(k, str) for k in keys]):
                raise TypeError("The keys must be a strings")
            if any([('\n' in k) for k in keys]):
                raise ValueError("Keys cannot contain newlines")
            indexed_counter += len(keys)
            value = list(data) + [score]

            # docid -> info final
            docid = ids_cnter
            ids_shelf[docid] = value
            ids_cnter += 1

            for key in keys:
                # keys -> docid
                # if the key (word) is new, create a new bucket (array)
                # every bucket has the ids of the index entries
                if key in key_shelf:
                    bucket = key_shelf[key]
                else:
                    # Lets use array, it's more compact in memory, and given that it
                    # should be easy for the caller to remove most repetitions,
                    # it should only get very little overhead
                    #
                    # NOTE: right now, at most one repetition per property is sent
                    # by cdpindex.py
                    bucket = key_shelf[key] = array.array('l')
                bucket.append(docid)

        if ids_cnter == 0:
            raise ValueError("No data to index")
        # prepare for serialization:
        # turn docsets into lists if delta-encoded integers (they're more compressible)
        logger.INFO(" Delta-encoding index buckets...")
        sys.stdout.flush()

        bucket_bytes = 0
        bucket_entries = 0
        bucket_maxentries = 0
        for key, docset in key_shelf.items():
            key_shelf[key] = delta_encode(docset)
            bucket_entries += len(docset)
            bucket_bytes += len(key_shelf[key])
            bucket_maxentries = max(bucket_maxentries, len(docset))

            assert delta_decode(key_shelf[key]) == set(docset), (
                "Delta-encoding error",
                docset,
            )

        logger.INFO("done")
        # print statistics

        logger.DEBUG("  Index contains:")
        logger.DEBUG("      ", len(key_shelf), "terms")
        logger.DEBUG("      ", bucket_entries, "entries")
        logger.DEBUG("      ", len(ids_shelf), "documents")
        logger.DEBUG("")
        logger.DEBUG("      ", len(key_shelf) // max(1, len(ids_shelf)), "terms on avg per documents")
        logger.DEBUG("")
        logger.DEBUG("  Bucket bytes", bucket_bytes)
        logger.DEBUG("  Bucket entries", bucket_entries)
        logger.DEBUG("  Bucket maximum size", bucket_maxentries)
        logger.DEBUG("  Avg bytes per entry", (float(bucket_bytes) / max(1, bucket_entries)))

        # save key
        # Format:
        #   ( matrix, docsets )
        #   Putting all keys togeter makes them more compressible.
        #   Sorting them (skeys) further helps.
        #   Joining them in a single string avoids pickling overhead
        #       (50% average with so many small strings)
        #   And keeping them joined in memory (FrozenStringList) helps
        #   avoid referencing overhead.

        sitems = sorted((k.encode("utf8"), v) for k, v in key_shelf.items())
        assert all(b"\n" not in k for k, v in sitems), "Terms cannot contain newlines"

        # free the big dict... eats up a lot
        del key_shelf

        logger.INFO(" Computing similitude matrix...")
        sys.stdout.flush()

        def progress_cb(p):
            logger.INFO("\r Computing similitude matrix...  %d%%\t" % int(p), file=sys.stderr)
            sys.stderr.flush()

        matrix = TermSimilitudeMatrix(map(operator.itemgetter(0), sitems),
                                      progress_callback=progress_cb)
        docsets = FrozenStringList(map(operator.itemgetter(1), sitems))
        del sitems

        logger.INFO("done")
        logger.INFO(" Saving:")

        keyfilename = os.path.join(directory, "compindex.key.xz")
        fh = CompressedFile(keyfilename, "wb")
        pickle.dump((matrix.pickle(), docsets.pickle()), fh, 2)
        logger.INFO("  Uncompressed keystore bytes", fh.tell())
        fh.close()

        fh = open(keyfilename, "rb")
        fh.seek(0, 2)
        logger.INFO("  Final keystore bytes", fh.tell())
        logger.INFO()
        fh.close()

        # split ids_shelf in N dicts of about ~16M pickled data each,
        # this helps get better compression ratios
        NB = sum(len(pickle.dumps(item, 2)) for item in ids_shelf.items())
        logger.INFO("  Total docstore bytes", NB)

        N = int((NB + DOCSTORE_BUCKET_SIZE / 2) // DOCSTORE_BUCKET_SIZE)
        if not N:
            N = 1
        logger.INFO("  Docstore buckets", N, "(", NB // N, " bytes per bucket)")
        all_idshelves = [{} for i in range(N)]
        for k, v in ids_shelf.items():
            cual = k % N
            all_idshelves[cual][k] = v

        # save dict where corresponds
        docucomp = 0
        doccomp = 0
        for cual, shelf in enumerate(all_idshelves):
            fname = "compindex-%02d.ids.xz" % cual
            idsfilename = os.path.join(directory, fname)
            fh = CompressedFile(idsfilename, "wb")
            pickle.dump(shelf, fh, 2)
            docucomp += fh.tell()
            fh.close()

            fh = open(idsfilename, "rb")
            fh.seek(0, 2)
            doccomp += fh.tell()
            fh.close()

        logger.INFO("  Docstore uncompressed bytes", docucomp)
        logger.INFO("  Docstore compressed bytes", doccomp)
        logger.INFO("")

        return indexed_counter
