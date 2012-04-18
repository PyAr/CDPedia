from twisted.internet import defer


class WorkerPool(object):
    """A twisted Worker Pool."""

    def __init__(self, size=30):
        self.size = size

    @defer.inlineCallbacks
    def _worker(self, function, iterable):
        """One worker instance."""
        while True:
            args = iterable.next()
            try:
                yield function(args)
            except Exception:
                pass

    def start(self, function, iterable):
        """Call the function for each set of args in iterable."""
        iterable = iter(iterable)
        workers = [self._worker(function, iterable) for n in range(self.size)]
        workers_d = defer.DeferredList(workers)
        return workers_d
