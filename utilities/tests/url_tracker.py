#! usr/bin/env python3

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

import queue
import os
import shutil
import sys
import threading
import urllib.request as request
import urllib.parse as parse
import urllib.error as error


LOCAL_HOST = 'http://127.0.0.1:8000'
stack = queue.Queue()


class _Track:
    """Match urls in CDPedia."""
    def __init__(self, url):
        self.url = url

    def verify_web(self):
        status, reason = self.get_html(self.url)
        result = (status, reason, self.url)
        if status != 200:
            _write_results(result)
        return status

    def get_html(self, link):
        """Extract request info."""
        try:
            html = request.urlopen(link)
            return html.status, html.reason
        except Exception as err:
            if isinstance(err, error.HTTPError):
                return err.code, err.reason


def _urls_to_verify(file_):
    """Extract urls/names to proccess."""
    urls = list()
    with open(file_, 'r', encoding='utf-8') as lines:
        for line in lines:
            # this is for the structure system save in files.
            url = '/'.join([LOCAL_HOST, 'wiki', line.split('|')[1]
                            if file_ == 'pag_elegidas.txt' else line.split()[0]])
            urls.append(url)
    return urls


def _clean_dir():
    if os.path.isdir('Pages_out'):
        shutil.rmtree('Pages_out')


def _create_result_dir():
    if not os.path.isdir('Pages_out'):
        os.mkdir('Pages_out')


def _write_results(data, name='results.txt'):
    with open('Pages_out/{}'.format(name), 'a', encoding='utf-8') as r:
        if os.stat('Pages_out/{}'.format(name)).st_size == 0:
            title = ' Status  Reason      Url_base\n\n'
            r.write(title)
        r.write('{:^9}{:<12}{}\n'.format(*data))


def _worker():
    inside, outside = 0, 0
    while True:
        url = stack.get()
        url_quote = parse.quote(url, safe='/:')
        tags = _Track(url_quote)
        result = tags.verify_web()
        if result == 200:
            inside += 1
        else:
            outside += 1
        stack.task_done()
        print('Testing pages in CDPedia {0} ·:|:· In Parallel Universe {1}\r'
              .format(inside, outside), end='')


def _main(file_=None):
    _clean_dir()
    _create_result_dir()
    select = 'pag_elegidas.txt' if not file_ else file_
    threading.Thread(target=_worker, daemon=True).start()
    urls = _urls_to_verify(select)
    print('Pages in this CDPedia version', len(urls))
    for url in urls:
        stack.put(url)
    stack.join()
    if not os.path.isfile('Pages_out/results.txt'):
        print('\nCongrats!! All pages are included in CDPedia')
    else:
        print('\nSomething outside, check results.txt in Pages_out folder')


if __name__ == '__main__':
    # please add 'pag_elegidas.txt' or 'all_articles.txt'
    # in root of this file and turn on cdpedia!
    if len(sys.argv) > 1:
        # Add other file.
        _main(file_=sys.argv[1])
    else:
        _main()
    print('Job Done')
