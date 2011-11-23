
"""The Searcher."""

import Queue
import collections
import threading
import uuid

# just a token to show the End Of Search
EOS = object()


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
