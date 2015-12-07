#!/usr/bin/python3

"""Build torrent and move files around in a CDPedia server."""

import hashlib
import os
import shutil
import subprocess
import sys

PROJ_DIR = 'CDPedia'
TORRENT_DIR = 'torrent'

TRACKERS = [
    'udp://tracker.openbittorrent.com:80',
    'udp://tracker.publicbt.com:80',
    'udp://tracker.ccc.de:80',
    'udp://tracker.istole.it:80',
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


def main(image_fname):
    """Main entry point."""
    parts = image_fname.split("-")
    lang = parts[1]
    dt = parts[3]
    print("Distributing image file {!r}".format(image_fname))
    print("    lang={!r}  date={!r}".format(lang, dt))
    image_fpath = os.path.join(PROJ_DIR, image_fname)

    # create the .torrent
    cmd = ['transmission-create', image_fpath]
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
    web_dir = os.path.join('www', 'images', lang, dt)
    print("Moving to web dir", repr(web_dir))
    if not os.path.exists(web_dir):
        os.mkdir(web_dir)
    shutil.move(torrent_file, web_dir)

    # save hashes
    print("Calculating hashes...")
    md5_value, sha1_value = _hasher(image_fpath)
    md5_fname = os.path.join(web_dir, image_fname + '.md5')
    print("Saving to {!r}: {}".format(md5_fname, md5_value))
    with open(md5_fname, 'wt') as fh:
        fh.write("{}  {}\n".format(md5_value, image_fname))
    sha1_fname = os.path.join(web_dir, image_fname + '.sha1')
    print("Saving to {!r}: {}".format(sha1_fname, sha1_value))
    with open(sha1_fname, 'wt') as fh:
        fh.write("{}  {}\n".format(sha1_value, image_fname))

    # send real file to torrent
    shutil.move(image_fpath, TORRENT_DIR)
    torrent_dir_abspath = os.path.abspath(TORRENT_DIR)
    torrent_file_abspath = os.path.abspath(os.path.join(web_dir, torrent_file))
    cmd = ['deluge-console', '--', 'add', '-p ' + torrent_dir_abspath, torrent_file_abspath]
    subprocess.call(cmd)
    cmd = ['deluge-console', 'info']
    subprocess.call(cmd)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: {} cdpedia_image_filename".format(sys.argv[0]))
        exit()

    fname = sys.argv[1]
    if '/' in fname:
        fname = fname.split('/')[-1]
    main(fname)
