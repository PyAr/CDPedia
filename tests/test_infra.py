# -*- coding: utf8 -*-

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

from __future__ import print_function, unicode_literals

import itertools
import os
import re
from codecs import open
from io import StringIO

import pytest
from flake8.api.legacy import get_style_guide

FLAKE8_OPTIONS = {'max_line_length': 99, 'select': ['E', 'W', 'F', 'C', 'N']}


def _get_python_filepaths():
    """Helper to retrieve paths of Python files."""
    python_paths = ['cdpedia.py', 'config.py', 'cdpetron.py']
    for root in ['src', 'utilities']:
        for dirpath, dirnames, filenames in os.walk(root):

            # Ignore third party code, at least until we appropiate them; related
            # issue: https://github.com/PyAr/CDPedia/issues/193 .
            if 'third_party' in dirnames:
                dirnames.remove('third_party')
            if 'bmp.py' in filenames:
                filenames.remove('bmp.py')

            for filename in filenames:
                if filename.endswith(".py"):
                    python_paths.append(os.path.join(dirpath, filename))
    return python_paths


def test_flake8(mocker):
    # verify all files are nicely styled
    python_filepaths = _get_python_filepaths()
    style_guide = get_style_guide(**FLAKE8_OPTIONS)
    fake_stdout = mocker.patch('sys.stdout')
    report = style_guide.check_files(python_filepaths)

    if report.total_errors != 0:
        issues = fake_stdout.getvalue().split('\n')
        msg = "Please fix the following flake8 issues!\n" + "\n".join(issues)
        pytest.fail(msg, pytrace=False)


def test_ensure_copyright():
    # all non-empty Python files must have a proper copyright somewhere in the first 5 lines
    issues = []
    regex = re.compile(r"\# Copyright \d{4}(-\d{4})? CDPedistas \(see AUTHORS\.txt\)$")
    for filepath in _get_python_filepaths():
        if os.stat(filepath).st_size == 0:
            continue

        with open(filepath, "r", encoding="utf8") as fh:
            for line in itertools.islice(fh, 5):
                if regex.match(line):
                    break
            else:
                issues.append(filepath)

    if issues:
        msg = "Please add copyright headers to the following files:\n" + "\n".join(issues)
        pytest.fail(msg, pytrace=False)
