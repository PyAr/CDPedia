# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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

# This is the recipe #498245: LRU cache decorator
# Author: Raymond Hettinger
# http://code.activestate.com/recipes/498245/

from collections import deque


def lru_cache(maxsize):
    '''Decorator applying a least-recently-used cache with the given maximum size.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    '''
    def decorating_function(f):
        cache = {}              # mapping of args to results
        queue = deque()         # order that keys have been accessed
        refcount = {}           # number of times each key is in the access queue
        def wrapper(*args):

            # localize variable access (ugly but fast)
            _cache=cache; _len=len; _refcount=refcount; _maxsize=maxsize
            queue_append=queue.append; queue_popleft = queue.popleft

            # get cache entry or compute if not found
            try:
                result = _cache[args]
                wrapper.hits += 1
            except KeyError:
                result = _cache[args] = f(*args)
                wrapper.misses += 1

            # record that this key was recently accessed
            queue_append(args)
            _refcount[args] = _refcount.get(args, 0) + 1

            # Purge least recently accessed cache contents
            while _len(_cache) > _maxsize:
                k = queue_popleft()
                _refcount[k] -= 1
                if not _refcount[k]:
                    if hasattr(_cache[k], "close"):
                        _cache[k].close()
                    del _cache[k]
                    del _refcount[k]

            # Periodically compact the queue by duplicate keys
            if _len(queue) > _maxsize * 4:
                for i in [None] * _len(queue):
                    k = queue_popleft()
                    if _refcount[k] == 1:
                        queue_append(k)
                    else:
                        _refcount[k] -= 1
                assert len(queue) == len(cache) == len(refcount) == sum(refcount.itervalues())

            return result
        wrapper.__doc__ = f.__doc__
        wrapper.__name__ = f.__name__
        wrapper.hits = wrapper.misses = 0
        return wrapper
    return decorating_function


if __name__ == '__main__':

    @lru_cache(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print f.hits, f.misses
