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

import datetime
import sys
import urllib.request as request
import urllib.parse as parse
import urllib.error as error


LOCAL_HOST = 'http://127.0.0.1:8000'


class Track:
    """Match urls in CDPedia."""
    instant = datetime.datetime.now()

    def __init__(self):
        self.file_name = 'results-{}.txt'.format(self.instant.strftime('%Y%m%d-%f'))
        self.aftermath = open(self.file_name, 'w', encoding='utf-8')
        self.title = ' Status  Reason      Url_base\n\n'
        self.aftermath.write(self.title)

    def verify_web(self, url):
        status, reason = self.get_html(url)
        result = (status, reason, url)
        if status != 200:
            self.aftermath.write('{:^9}{:<12}{}\n'.format(*result))
        return status

    def get_html(self, link):
        """Extract request info."""
        try:
            html = request.urlopen(link)
            return html.status, html.reason
        except Exception as err:
            if isinstance(err, error.HTTPError):
                return err.code, err.reason
            else:
                raise err


def urls_to_verify(file_):
    """Extract urls/names to proccess."""
    urls = list()
    with open(file_, 'r', encoding='utf-8') as lines:
        for line in lines:
            # pag_elegidas.txt has multiple columns
            if '|' in line:
                name = line.split('|')[1]
            # just the page name, like all_articles.txt
            else:
                name = line.split()[0]
            url = '/'.join([LOCAL_HOST, 'wiki', name])
            urls.append(url)
    return urls


def main(file_='pag_elegidas.txt'):
    urls = urls_to_verify(file_)
    print('Pages in this CDPedia version', len(urls))
    inside, outside = 0, 0
    tags = Track()
    for url in urls:
        url_quote = parse.quote(url, safe='/:')
        result = tags.verify_web(url_quote)
        if result == 200:
            inside += 1
        else:
            outside += 1
        print('Testing pages in CDPedia {0} ·:|:· In Parallel Universe {1}\r'
              .format(inside, outside), end='')
    if outside == 0:
        tags.aftermath.write(chr(128126))
        print('\nCongrats!! All pages are included in CDPedia')
    else:
        print('\nSomething outside, check results.txt')
    tags.aftermath.close()


if __name__ == '__main__':
    # please add 'pag_elegidas.txt' or 'all_articles.txt'
    # in root of this file and turn on cdpedia!
    if len(sys.argv) > 1:
        # Add other file.
        main(file_=sys.argv[1])
    else:
        main()
    print('Job Done')
