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
# For further info, check  http://code.google.com/p/cdpedia/

"""Download the HTML python documentation that will be included in realease."""

import logging
import os
import shutil
import urllib.request

import config

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.9.0.5) Gecko/2008121622 '
        'Ubuntu/8.10 (intrepid) Firefox/3.0.5')
}

logger = logging.getLogger('scraping.pydocs')


def _tarball_info(lang, lang_config, dumpbase):
    """Get documentation tarball url and path."""
    # python docs URL must exist, otherwise raise KeyError
    url = lang_config['python_docs']
    filedir = os.path.join(dumpbase, 'pydocs')
    filename = lang + '_' + os.path.basename(url)
    filepath = os.path.join(filedir, filename)
    exists = os.path.isfile(filepath)
    return url, filepath, filename, exists


def download(lang, lang_config, dumpbase):
    """Download python documentation tarball."""
    url, filepath, filename, exists = _tarball_info(lang, lang_config, dumpbase)
    if exists:
        logger.info('Python documentation already downloaded: %s', filename)
        return

    logger.info('Downloading python documentation: %s', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    u = urllib.request.urlopen(req)
    data = u.read()
    with open(filepath, "wb") as fh:
        fh.write(data)
    logger.info('Documentation successfuly downloaded')


def clone(lang, lang_config, dumpbase):
    """Copy python docs archive from dump to cdroot."""
    url, filepath, filename, exists = _tarball_info(lang, lang_config, dumpbase)
    dest = os.path.join(config.DIR_ASSETS, config.PYTHON_DOCS_FILENAME)
    logger.info('Copying python docs')
    shutil.copy(filepath, dest)
