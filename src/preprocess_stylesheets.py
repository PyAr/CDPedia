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

import argparse
import functools
import logging
import os
import re
import urllib.request
import urllib.error
import urllib.parse

import bs4


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
        'Ubuntu/8.10 (intrepid) Firefox/3.0.5')
}

MAIN_CSS_NAME = "wikipedia.css"
LOCAL_STATIC_URL = "/static/css/assets/"

logger = logging.getLogger(__name__)


def get_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        u = urllib.request.urlopen(req)
        return u.read()
    except:
        logger.exception('')

def download_and_replace(match, url_wikipedia, outdir):
    internal_resource_url = match.groups()[0] # for example '/static/images/project-logos/eswiki-2x.png'
    logger.debug("Discovered CSS resource %s", internal_resource_url)

    internal_resource_url = internal_resource_url.replace('"', '') # some cleaning

    if internal_resource_url.startswith("//"): # absolute url
        url = "https://" + internal_resource_url[2:]
    else:
        url = url_wikipedia + internal_resource_url[1:]

    # Download all the resources in a very simple way, all the files in the same directory
    # droping the subdirectories and do a cleanup of the filenames to
    filename = os.path.basename(internal_resource_url)
    filename = urllib.parse.unquote(filename)
    filename = filename.encode("ascii", errors='ignore').decode("ascii")
    filename = filename.split("?")[0] # remove trailing version eg "asd.png?123"
    file_path = os.path.join(outdir, filename)
    if not os.path.exists(file_path):
        asset = get_url(url)
        if not asset:
            logger.debug("Can't find file at %r", url)
            return "url(nofile)"

        with open(file_path, "wb") as f:
            f.write(asset)

    url_data = "url(%s)" % (LOCAL_STATIC_URL + filename)
    logger.debug("  saved as %r with url %r", file_path, url_data)
    return url_data


def process_css(url_wikipedia, outdir):
    logger.info("Starting to pre-process CSS")
    index_page = get_url(url_wikipedia)

    soup = bs4.BeautifulSoup(index_page, "lxml")
    soup.find_all('link', {'rel':"stylesheet"})

    css_files = []
    for css_link in soup.find_all('link', {'rel':"stylesheet"}):
        url = url_wikipedia + css_link.attrs['href']
        logger.debug("downloading %r", url)
        css = get_url(url)
        css_files.append(css.decode("utf-8"))

    css_data = "\n".join(css_files)

    replace_func = functools.partial(download_and_replace, url_wikipedia=url_wikipedia, outdir=outdir)
    css_data = re.sub("url\((.*?)\)", replace_func, css_data)
    return css_data


if __name__ == '__main__':
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Download Wikipedia stylesheets')
    parser.add_argument('language', help='Target language')
    parser.add_argument('outdir', help='Path to download the files')

    args = parser.parse_args()

    URL_WIKIPEDIA = "https://{}.wikipedia.org/".format(args.language)

    # TODO: outdir = args.outdir + args.language

    css = process_css(URL_WIKIPEDIA, args.outdir)
    with open(os.path.join(args.outdir, MAIN_CSS_NAME), "w") as f:
        f.write(css)

