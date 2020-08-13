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

"""
Usage: python make_autorun.py <cdpedia_image_dir> [temp_dir]

See instructions and setup requirements in resources/autorun.win/HOWTO.txt

"""

import logging
import os
import shutil
import struct
import subprocess
import sys
import tempfile

logger = logging.getLogger('make_autorun')

if os.name != 'nt':
    logger.error('This script is meant to be run on Windows.')
    sys.exit()

if struct.calcsize("P") != 4:
    # void pointer size of a 32 bit python interpreter is 4 bytes
    logger.error('This script is meant to be run on 32 bit python')
    sys.exit()


def build_exe(imagedir, tempdir=None):
    """Create a single executable for running CDPedia on Windows."""

    logger.info('Generating cdpedia.exe')
    imagedir = os.path.abspath(imagedir)
    projdir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    logger.debug('Project dir: %s', projdir)
    logger.debug('Image dir: %s', imagedir)
    if tempdir is None:
        tempdir = os.path.abspath(tempfile.gettempdir())
    tempdir = os.path.abspath(tempdir)
    logger.debug('Temp dir: ' + tempdir)

    script = os.path.join(imagedir, 'cdpedia.py')
    templates = os.path.join(imagedir, 'cdpedia', 'src', 'web', 'templates')
    icon = os.path.join(projdir, 'resources', 'autorun.win', 'cdroot', 'cdpedia.ico')
    pyinstaller = os.path.join(os.environ['VIRTUAL_ENV'], 'Scripts', 'pyinstaller.exe')

    cmd = [
        pyinstaller,
        '--onefile',
        '--noupx',
        '--noconsole',
        '--paths', os.path.join(imagedir, 'cdpedia'),
        '--paths', os.path.join(imagedir, 'cdpedia', 'extlib'),
        '--add-data', '{};src/web/templates'.format(templates),
        '--icon', icon,
        '--distpath', imagedir,
        '--specpath', tempdir,
        '--workpath', tempdir,
        os.path.abspath(script)
    ]

    if not subprocess.call(cmd, cwd=os.path.dirname(pyinstaller)):
        src = os.path.join(imagedir, 'cdpedia.exe')
        dst = os.path.join(projdir, 'resources', 'autorun.win', 'cdroot', 'cdpedia.exe')
        shutil.copyfile(src, dst)
        logger.info('cdpedia.exe correctly generated')
    else:
        logger.error('Could not generate cdpedia.exe correctly')


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.DEBUG, format='%(name)-6s %(levelname)-6s %(message)s')

    build_exe(*sys.argv[1:])
