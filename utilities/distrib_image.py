#!/usr/bin/python3

# Copyright 2015-2020 CDPedistas (see AUTHORS.txt)
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

"""Build torrent and move files around in a CDPedia server.

Packages needed in the system:

    - transmission-cli
    - deluge-console
    - deluged

"""

import hashlib
import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)

TRACKERS = [
    'udp://tracker.openbittorrent.com:80',
    'udp://tracker.opentrackr.org:1337',
    'udp://tracker.coppersurfer.tk:6969',
    'udp://tracker.leechers-paradise.org:6969',
    'udp://zer0day.ch:1337',
    'udp://explodie.org:6969',
]


def _hasher(fname):
    """Calculate md5 and sha1 from a file's content."""
    md5hash = hashlib.md5()
    sha1hash = hashlib.sha1()
    with open(fname, 'rb') as fh:
        while True:
            data = fh.read(65536)
            if not data:
                break
            md5hash.update(data)
            sha1hash.update(data)
    return md5hash.hexdigest(), sha1hash.hexdigest()


def main(wwwdir, torrentdir, image_filepath):
    """Main entry point."""
    image_fname = os.path.basename(image_filepath)
    parts = image_fname.split("-")
    lang = parts[1]
    dt = parts[3]
    logger.INFO("Distributing image file {!r}".format(image_filepath))
    logger.INFO("    lang={!r}  date={!r}".format(lang, dt))

    # create the .torrent
    cmd = ['transmission-create', image_filepath]
    for t in TRACKERS:
        cmd.append('-t')
        cmd.append(t)
    subprocess.call(cmd)
    torrent_file = image_fname + '.torrent'
    assert os.path.exists(torrent_file)

    # fix torrent file permission
    cmd = ['chmod', '664', torrent_file]
    subprocess.call(cmd)

    # create the destination directory if not there, and move the torrent file
    web_dir = os.path.join(wwwdir, 'images', lang, dt)
    logger.INFO("Moving to web dir", repr(web_dir))
    if not os.path.exists(web_dir):
        os.makedirs(web_dir)
    shutil.move(torrent_file, web_dir)

    # save hashes
    logger.INFO("Calculating hashes...")
    md5_value, sha1_value = _hasher(image_filepath)
    md5_fname = os.path.join(web_dir, image_fname + '.md5')
    logger.INFO("Saving to {!r}: {}".format(md5_fname, md5_value))
    with open(md5_fname, 'wt') as fh:
        fh.write("{}  {}\n".format(md5_value, image_fname))
    sha1_fname = os.path.join(web_dir, image_fname + '.sha1')
    logger.INFO("Saving to {!r}: {}".format(sha1_fname, sha1_value))
    with open(sha1_fname, 'wt') as fh:
        fh.write("{}  {}\n".format(sha1_value, image_fname))

    # send real file to torrent
    shutil.move(image_filepath, torrentdir)
    torrent_dir_abspath = os.path.abspath(torrentdir)
    torrent_file_abspath = os.path.abspath(os.path.join(web_dir, torrent_file))
    cmd = ['deluge-console', '--', 'add', '-p ' + torrent_dir_abspath, torrent_file_abspath]
    subprocess.call(cmd)
    cmd = ['deluge-console', 'info']
    subprocess.call(cmd)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        logger.INFO("Usage: {} www_dir torrent_dir cdpedia_image_filename".format(sys.argv[0]))
        exit()

    wwwdir, torrentdir, image_filepath = sys.argv[1:]
    main(wwwdir, torrentdir, image_filepath)
