#!/usr/bin/env python

# Copyright 2012-2017 CDPedistas (see AUTHORS.txt)
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
# For further info, check  https://launchpad.net/cdpedia/

"""Generate the list of articles inside some Namespaces."""

import json
import logging
import urllib
import urllib2
import time

# these is the list of the namespaces we'll get; to get this you can
# check the whole list with the following site-info meta-query:
#     http://es.wikipedia.org/w/api.php?
#     action=query&meta=siteinfo&siprop=namespaces&format=json
NAMESPACES = (
    14,  # Category
    12,  # Help
    104,  # Anexo
    100,  # Portal
)

API_URL = (
    'http://%(language)s.wikipedia.org/w/api.php?action=query&list=allpages'
    '&apcontinue=%(contin)s&aplimit=500&format=json&apnamespace=%(namespace)s'
)

logger = logging.getLogger("list_nspaces")


def retryable(func):
    """Decorator to retry functions."""
    def _f(*args, **kwargs):
        """Retryable function."""
        delay = 1
        for attempt in range(50, -1, -1):  # if reaches 0: no more attempts
            try:
                res = func(*args, **kwargs)
            except Exception as err:
                if not attempt:
                    raise
                logger.debug("Problem (retrying after %ds): %s", delay, err)
                time.sleep(delay)
                delay *= 2
                if delay > 300:
                    delay = 300
            else:
                return res
    return _f


@retryable
def hit_api(**kwords):
    url = API_URL % kwords
    logger.debug("Hit %r", url)
    u = urllib2.urlopen(url)
    data = json.load(u)
    return data


def get_articles(language, test_limit):
    """Get all the articles for some namespaces."""
    test_limit = int(test_limit) if test_limit else None
    for namespace in NAMESPACES:
        contin = ''
        logger.debug("Getting namespace %r", namespace)
        while True:
            data = hit_api(language=language, namespace=namespace,
                           contin=contin)
            try:
                items = data['query']['allpages']
            except KeyError:
                # no pages for the given namespace
                break

            for item in items:
                title = item['title'].replace(" ", "_")
                yield title

            # check test limit, if any
            if test_limit is not None:
                test_limit -= len(items)
                if test_limit <= 0:
                    break

            # continue, if needed
            if 'continue' in data:
                contin = data['continue']['apcontinue']
                contin = urllib.quote(contin.encode('utf8'))
            else:
                break


if __name__ == '__main__':
    with open('articles_by_namespaces.txt', 'wb') as fh:
        for link in get_articles('es'):
            fh.write(link.encode('utf8') + '\n')
