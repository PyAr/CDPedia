from twisted.internet import defer, reactor
from twisted.trial.unittest import TestCase
from workerpool import WorkerPool


class WorkerPoolTestCase(TestCase):
    """Test the WorkerPool class."""

    @defer.inlineCallbacks
    def test_start(self):
        """Test the WorkerPool.start class."""

        @defer.inlineCallbacks
        def squaring_processor(n):
            """A fake processor that squares."""
            d = defer.succeed(n ** 2)
            result = yield d
            results.append(result)

        wp = WorkerPool(3)
        results = []

        yield wp.start(squaring_processor, range(10))
        self.assertEqual(results, [n ** 2 for n in range(10)])
