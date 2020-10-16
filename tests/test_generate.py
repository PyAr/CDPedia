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

import pytest

import config
from src.generate import copy_dir, _copy_css


@pytest.fixture
def dirtree(tmp_path):
    """Simple directory structure including some files."""
    dirs = [tmp_path / d for d in ('d', 'd/d1', 'd/d1/d11', 'd/d2', 'd/d2/d21')]
    files = []
    for d in dirs:
        d.mkdir()
        for f in ('foo.txt', '.foo', 'foo.pyc'):
            files.append(d / f)
            files[-1].touch()
    return str(dirs[0])


@pytest.mark.parametrize('create_dest', (True, False))
def test_copy_dir(tmp_path, dirtree, create_dest):
    """Check that directory tree is copied as expected."""
    dest = tmp_path / 'dest'
    if create_dest:
        dest.mkdir()
    copy_dir(dirtree, str(dest))
    assert len(list(dest.rglob('*.txt'))) == 5
    assert len(list(dest.rglob('*.pyc'))) == 0
    assert len(list(dest.rglob('.*'))) == 0


def test_copy_dir_ignore_subdir(tmp_path, dirtree):
    """Check that ignored subdirs are not copied."""
    dest = tmp_path / 'dest'
    ignore = 'd1', 'd21'
    copy_dir(dirtree, str(dest), *ignore)
    assert not (dest / 'd1').exists()
    assert not (dest / 'd2/d21').exists()
    assert len(list(dest.rglob('*.txt'))) == 2


def test_copy_css(tmp_path):
    """Check transfering final CSS and associated resources."""
    src_base = tmp_path / 'src'
    dst_base = tmp_path / 'dst'
    # create expected layout
    css_dir = src_base.joinpath(config.DIR_SOURCE_ASSETS, config.CSS_DIRNAME)
    res_dir = css_dir / config.CSS_RESOURCES_DIRNAME
    res_dir.mkdir(parents=True)
    # create couple of files
    (css_dir / config.CSS_FILENAME).touch()
    (css_dir / 'foo.css').touch()  # should not be copied
    (res_dir / 'bar.png').touch()
    (res_dir / 'baz.ico').touch()
    _copy_css(str(src_base), str(dst_base))
    css = list(dst_base.rglob('*.css'))
    assert len(css) == 1
    assert css[0].name == config.CSS_FILENAME
    assert len(list(dst_base.rglob('ba*'))) == 2
