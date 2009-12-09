# -*- coding: utf8 -*-

import cPickle
import os
import random
import config
import array
import sys
import bisect
import operator
from bz2 import BZ2File as CompressedFile

from lru_cache import lru_cache



if config.ENABLE_INDEX_COMPRESSION:

    def delta_encode(docset, sorted=sorted, with_reps=False):
        pdoc = -1
        rv = array.array('B')
        rva = rv.append
        flag = (0,0x80)
        for doc in sorted(docset):
            if with_reps or doc != pdoc:
                if not with_reps and doc<=pdoc:
                    # decreasing sequence element escaped by 0 delta entry
                    rva(0)
                    pdoc = -1
                doc, pdoc = doc-pdoc, doc
                while True:
                    b = doc & 0x7F
                    doc >>= 7
                    b |= flag[doc != 0]
                    rva(b)
                    if not doc:
                        break
        return rv.tostring()

    def delta_decode(docset, ctor=set, append='add', with_reps=False):
        doc = 0
        pdoc = -1
        rv = ctor()
        rva = getattr(rv,append)
        shif = 0
        abucket = array.array('B')
        abucket.fromstring(docset)
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

else:

    def delta_encode(docset, **kw):
        return docset

    def delta_decode(docset, **kw):
        return docset

    def delta_encode_str(docset, **kw):
        return cPickle.dumps(docset,2)
    
    def delta_decode_str(docset, **kw):
        return cPickle.loads(docset)


class FrozenStringList:
    def __init__(self, iterable=None):
        self.index = array.array('l',[0])
        self.heap = ""
        if iterable:
            self.extend(iterable)
    
    def __getitem__(self, ix):
        if ix < 0:
            raise IndexError, "Negative index"
        elif ix >= (len(self.index)-1):
            raise IndexError, "FrozenStringList index out of range"
        else:
            index = self.index
            return self.heap[ index[ix] : index[ix+1] ]

    def __len__(self):
        return len(self.index)-1
    
    def __iter__(self):
        for i in xrange(len(self)):
            yield self[i]
    
    def __str__(self):
        #return str( (self.index, self.heap) )
        return str(list(self))
    
    def __repr__(self):
        #return "%s(%r) #%r" % (self.__class__.__name__, list(self), (self.index, self.heap))
        return "%s(%r)" % (self.__class__.__name__, list(self))
    
    def append(self, value):
        if not isinstance(value, str):
            raise TypeError, "String expected"
            
        self.index.append( len(self.heap) + len(value) )
        self.heap += value
    
    def extend(self, iterable):
        iterable = list(iterable)
        
        len_ = len
        index_a = self.index.append
        pos = len_(self.heap)
        for s in iterable:
            pos += len_(s)
            index_a(pos)
        
        self.heap += ''.join(iterable)
    
    def pickle(self):
        return (delta_encode_str(self.index, 
                    sorted=lambda x:x, 
                    with_reps=True), 
                self.heap)
    
    @staticmethod
    def unpickle(data):
        rv = FrozenStringList()
        rv.index = delta_decode_str(data[0], 
            ctor=(lambda:array.array('l')),
            append='append',
            with_reps=True)
        rv.heap = data[1]
        return rv

class TermSimilitudeMatrixBase:
    def __init__(self, terms = [], progress_callback = lambda : None):
        self.terms = terms = FrozenStringList(sorted(terms))
        self.matrix = matrix = FrozenStringList()
        
        if terms:
            similar = self.similar_impl
            self.init_similar_impl()
            matrix_a = matrix.append
            
            N = len(terms)
            for i,t1 in enumerate(terms):
                bucket = array.array('l')
                bucket_a = bucket.append
                valid = False
                for i2 in similar(t1):
                    if i != i2: # <- omit the diagonal, which is implicit
                        bucket_a(i2)
                    else:
                        valid = True
                assert valid, "Invalid bucket - the term must match to itself"
                matrix_a( delta_encode_str(bucket) )
                
                if not (i % 100):
                    progress_callback(i*100.0/N)
    
    def init_similar_impl(self):
        """
        Si hace falta inicializar algo para 'similar', hacerlo acá.
        Se llama antes de llamar a similar.
        Los términos (en el orden de sus ids) están en self.terms.
        """
        pass
    
    def similar_impl(self, t):
        """
        Iterable sobre los índices de términos similares a t.
        """
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
        """
        Returns the index for the specified term, 
        raises KeyError if not found
        """
        i = bisect.bisect_left(self.terms, t)
        if i >= len(self.terms) or self.terms[i] != t:
            raise KeyError, t
        
        return i
    
    def lookup_term_value(self, i):
        """
        Returns the text for the specified term index. 
        Raises IndexError if the index is invalid
        """
        return self.terms[i]
    
    def contains_term(self, t):
        try:
            self.lookup_term_index(t)
            return True
        except KeyError,e:
            return False
    
    def similar_terms(self, t):
        """
        Returns an iterable over the indices of similar terms.
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
        for tv in iter( t[a:a+l] 
                        for l in xrange(min(20,len(t)),0,-1)
                        for a in xrange(len(t)-l+1) ):
            if self.contains_term(t):
                # an exact match is a godsend - we just look it up
                i = self.lookup_term_index(t)
                candidates = delta_decode_str(self.matrix[i])
                candidates.add(i) # <- the matrix omits the diagnoal
                break
        else:
            # ouch... no substring found in the matrix.
            # We must do things the slow way then...
            # NOTE: this should be most unlikely, since most alphabet
            #   letters should be in the index and thus in the matrix.
            candidates = set()
            candidates_a = candidates.add
            for i,st in enumerate(self.terms):
                if terms[i] in t:
                    # Found a substring in the matrix, all matches
                    # will be a subset of matches for the substring
                    candidates = delta_decode_str(self.matrix[i])
                    candidates.add(i) # <- the matrix omits the diagnoal
                    break
                elif t in terms[i]:
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
        def init_similar_impl(self):
            self.stree = stree = SuffixTree.SubstringDict()
            for i,t in enumerate(self.terms):
                stree[t] = i
            
        def similar_impl(self, t):
            # SuffixTree tiende a generar muchas repeticiones
            return set(self.stree[t])
    
except ImportError:
    print "WARNING: SuffixTree no está instalado, la generación de la matriz de similitud de términos puede ser LENTA"

    class TermSimilitudeMatrix(TermSimilitudeMatrixBase):
        def similar_impl(self, t):
            for i,st in enumerate(self.terms):
                if t in st:
                    yield i


class Index(object):
    '''Handles the index.'''

    def __init__(self, directory):
        self._directory = directory

        # open the key shelve
        # Format:
        #   ( matrix, docsets )
        #   matrix = TermSimilitudeMatrix
        #   docsets = FrozenStringList
        keyfilename = os.path.join(directory, "easyindex.key.bz2")
        fh = CompressedFile(keyfilename, "rb")
        matrix, docsets = cPickle.load(fh)
        fh.close()
        
        matrix = TermSimilitudeMatrix.unpickle(matrix)
        docsets = FrozenStringList.unpickle(docsets)
        
        self.matrix, self.docsets = matrix, docsets
        
        # see how many id files we have
        idsfilename = os.path.join(directory, "easyindex-*.ids.bz2")
        filenames = []
        for fn in os.listdir(directory):
            if fn.startswith("easyindex-") and \
                fn.endswith(".ids.bz2"):
                filenames.append(fn)
        self.idfiles_count = len(filenames)

    @lru_cache(config.DOCSTORE_CACHE_SIZE)
    def _get_ids_shelve(self, cual):
        '''Return the ids index.'''
        fname = os.path.join(self._directory, "easyindex-%02d.ids.bz2" % cual)
        fh = CompressedFile(fname, "rb")
        idx = cPickle.load(fh)
        fh.close()
        return idx

    def _get_info_id(self, allids):
        '''Returns the values for the given ids.

        As it groups the ids according to the file, is much faster than
        retrieving one by one.
        '''
        # group the id per file
        cuales = {}
        cualesg = cuales.get
        ocual = None
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
        '''Returns an iterator over the stored items.'''
        matrix = self.matrix
        doc_lookup = self._get_info_id
        for i, docset in enumerate(self.docsets):
            key = matrix.lookup_term_value(i).decode("utf8")
            values = doc_lookup(delta_decode(docset))
            yield key, list(values)

    def values(self):
        '''Returns an iterator over the stored values.'''
        matrix_lookup = self.matrix.lookup_term_value
        doc_lookup = self._get_info_id
        for i, docset in enumerate(self.docsets):
            values = doc_lookup(delta_decode(docset))
            for v in values:
                yield v

    def keys(self):
        return self.matrix.terms

    def random(self):
        '''Returns a random value.'''
        cual = random.randint(0, self.idfiles_count - 1)
        idx = self._get_ids_shelve(cual)
        return random.choice(idx.values())

    def __contains__(self, key):
        '''Returns if the key is in the index or not.'''
        return self.matrix.contains_term(key.encode("utf8"))

    def search(self, keys):
        '''Returns all the values that are found for those keys.

        The AND boolean operation is applied to the keys.
        '''
        results = None
        matrix = self.matrix
        docsets = self.docsets
        for key in keys:
            key = key.encode("utf8")
            if not matrix.contains_term(key):
                continue
            allids = delta_decode(docsets[matrix.lookup_term_index(key)])
            if results is None:
                results = allids
            else:
                results &= allids

        if not results:
            return []

        # do AND between results, and get the values from ids
        return self._get_info_id(results)

    def partial_search(self, keys):
        '''Returns all the values that are found for those partial keys.

        The received keys are taken as part of the real keys (suffix,
        preffix, or in the middle).

        The AND boolean operation is applied to the keys.
        '''
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
            if not isinstance(key, basestring):
                raise TypeError("The key must be string or unicode")
            if '\n' in key:
                raise ValueError("Key cannot contain newlines")

            # docid -> info final
            if value in tmp_reverse_id:
                docid = tmp_reverse_id[value]
            else:
                docid = ids_cnter
                tmp_reverse_id[value] = docid
                ids_shelf[docid] = value
                ids_cnter += 1
            
            # keys -> docid
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

        # prepare for serialization:
        # turn docsets into lists if delta-encoded integers (they're more compressible)
        print " Delta-encoding index buckets...",
        sys.stdout.flush()
        
        bucket_bytes = 0
        bucket_entries = 0
        bucket_maxentries = 0
        for key, docset in key_shelf.iteritems():
            key_shelf[key] = delta_encode(docset)
            bucket_entries += len(docset)
            bucket_bytes += len(key_shelf[key])
            bucket_maxentries = max(bucket_maxentries, len(docset))
            
            assert delta_decode(key_shelf[key]) == set(docset), \
                ("Delta-encoding error", docset)

        print "done"

        # print statistics

        print "  Index contains:"
        print "      ", len(key_shelf), "terms"
        print "      ", bucket_entries, "entries"
        print "      ", len(ids_shelf), "documents"
        print        
        print "      ", len(key_shelf) // max(1,len(ids_shelf)), "terms on avg per documents"
        print
        print "  Bucket bytes", bucket_bytes
        print "  Bucket entries", bucket_entries
        print "  Bucket maximum size", bucket_maxentries
        print "  Avg bytes per entry", (float(bucket_bytes) / max(1,bucket_entries))

        # save key
        # Format:
        #   ( matrix, docsets )
        #   Putting all keys togeter makes them more compressible.
        #   Sorting them (skeys) further helps.
        #   Joining them in a single string avoids pickling overhead 
        #       (50% average with so many small strings)
        #   And keeping them joined in memory (FrozenStringList) helps
        #   avoid referencing overhead.
        
        sitems = sorted([ (k.encode("utf8"),v) 
                          for k,v in key_shelf.iteritems() ])
        assert all('\n' not in k for k,v in sitems), \
            "Terms cannot contain newlines"
        
        # free the big dict... eats up a lot
        del key_shelf
        
        print " Computing similitude matrix...",
        sys.stdout.flush()

        
        def progress_cb(p):
            print >> sys.stderr, "\r Computing similitude matrix...  %d%%\t" % int(p),
            sys.stderr.flush()
        
        matrix = TermSimilitudeMatrix(map(operator.itemgetter(0), sitems),
                progress_callback = progress_cb)
        docsets = FrozenStringList(map(operator.itemgetter(1), sitems))
        del sitems
        
        print "done"
        print " Saving:"
        
        keyfilename = os.path.join(directory, "easyindex.key.bz2")
        fh = CompressedFile(keyfilename, "wb")
        cPickle.dump( (matrix.pickle(), docsets.pickle()), fh, 2)
        print "  Uncompressed keystore bytes", fh.tell()
        fh.close()
        
        fh = open(keyfilename, "rb")
        fh.seek(0,2)
        print "  Final keystore bytes", fh.tell()
        print
        fh.close()

        # split ids_shelf in N dicts of about ~16M pickled data each,
        # this helps get better compression ratios
        NB = sum( len(cPickle.dumps(item,2)) for item in ids_shelf.iteritems() )
        print "  Total docstore bytes", NB
        
        N = int((NB + config.DOCSTORE_BUCKET_SIZE/2) // config.DOCSTORE_BUCKET_SIZE)
        if not N:
            N = 1
        print "  Docstore buckets", N, "(", NB//N, " bytes per bucket)"
        all_idshelves = [{} for i in xrange(N)]
        for k,v in ids_shelf.iteritems():
            cual = k % N
            all_idshelves[cual][k] = v

        # save dict where corresponds
        docucomp = 0
        doccomp = 0
        for cual, shelf in enumerate(all_idshelves):
            fname = "easyindex-%02d.ids.bz2" % cual
            idsfilename = os.path.join(directory, fname)
            fh = CompressedFile(idsfilename, "wb")
            cPickle.dump(shelf, fh, 2)
            docucomp += fh.tell()
            fh.close()
            
            fh = open(idsfilename, "rb")
            fh.seek(0,2)
            doccomp += fh.tell()
            fh.close()
            
        print "  Docstore uncompressed bytes", docucomp
        print "  Docstore compressed bytes", doccomp
        print

        return indexed_counter

