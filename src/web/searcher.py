# -*- coding: utf-8 -*-
"""The Searcher."""

import Queue
import collections
import operator
import re
import threading
import uuid

# just a token to show the End Of Search
EOS = object()

# regex used in untested code, see get_grouped() below
LIMPIA = re.compile("[(),]")

class Cache(dict):
    """A dict-like, but with a max limit."""
    def __init__(self, limit, discard_func):
        self._limit = limit
        self._discard_func = discard_func
        self._items = collections.deque()
        super(Cache, self).__init__()

    def __setitem__(self, key, value):
        if key not in self:
            self._items.append(key)
            # limit the size of the cache
            if len(self._items) > self._limit:
                too_old = self._items.popleft()
                old_item = super(Cache, self).pop(too_old)
                self._discard_func(old_item)
        super(Cache, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(Cache, self).__delitem__(key)
        self._items.remove(key)


class ThreadedSearch(threading.Thread):
    """The real search, in other thread."""
    def __init__(self, index, words):
        self.queue = Queue.Queue()
        self.index = index
        self.words = words
        self.discarded = False
        super(ThreadedSearch, self).__init__()

    def run(self):
        """Do the search."""
        # full match
        result = self.index.search(self.words)
        if self.discarded:
            return

        for r in result:
            self.queue.put(r)
            if self.discarded:
                return

        # partial
        result = self.index.partial_search(self.words)
        if self.discarded:
            return

        for r in result:
            self.queue.put(r)
            if self.discarded:
                return

        # done
        self.queue.put(EOS)


class Searcher(object):
    """Searcher object for the web interface."""

    def __init__(self, index, cache_size):
        self.index = index
        self.active_searches = Cache(cache_size, self.discard_item)

    def discard_item(self, search_item):
        """Discard the search."""
        search, _, _ = search_item
        search.discarded = True

    def start_search(self, words):
        """Start the search."""
        search_id = str(uuid.uuid4())
        ts = ThreadedSearch(self.index, words)
        self.active_searches[search_id] = (ts, [], threading.Lock())
        ts.start()
        return search_id

    def get_results(self, search_id, start=0, quantity=10):
        """Get results from the search."""
        search, prev_results, lock = self.active_searches[search_id]

        # maybe the requested results are already retrieved from index
        need_to_retrieve = start + quantity - len(prev_results)
        if not need_to_retrieve:
            return prev_results[start:start+quantity]

        with lock:
            # we need to get more results from index
            for _ in xrange(need_to_retrieve):
                result = search.queue.get()
                if result is EOS:
                    break
                prev_results.append(result)

            self.active_searches[search_id] = (search, prev_results, lock)
        return prev_results[start:start+quantity]

    def get_grouped(self, search_id, quantity=10):
        """Get the results, old fashion grouped.

        WARNING: this code is untested, but it's basically the old grouping
        code that used to live in server.py.
        """
        candidatos = self.get_results(search_id, quantity=quantity)

        # -------------- start of old untested code --------------------

        # agrupamos por link, dando prioridad a los títulos de los
        # artículos originales
        agrupados = {}
        for link, titulo, ptje, original, texto in candidatos:
            # quitamos 3 dirs del link y agregamos "wiki"
            link = u"wiki" + link[5:]

            # los tokens los ponemos en minúscula porque las mayúscula les
            # da un efecto todo entrecortado
            tit_tokens = set(LIMPIA.sub("", x.lower()) for x in titulo.split())

            if link in agrupados:
                (tit, prv_ptje, tokens, txt) = agrupados[link]
                tokens.update(tit_tokens)
                if original:
                    # guardamos la info del artículo original
                    tit = titulo
                    txt = texto
                agrupados[link] = (tit, prv_ptje + ptje, tokens, txt)
            else:
                agrupados[link] = (titulo, ptje, tit_tokens, texto)

        # limpiamos los tokens
        for link, (tit, ptje, tokens, texto) in agrupados.iteritems():
            tit_tokens = set(LIMPIA.sub("", x.lower()) for x in tit.split())
            tokens.difference_update(tit_tokens)

        # ordenamos la nueva info descendiente y devolvemos todo
        candidatos = ((k,) + tuple(v) for k,v in agrupados.iteritems())
        return sorted(candidatos, key=operator.itemgetter(2), reverse=True)
