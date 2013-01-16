#!/usr/bin/env python

# Copyright 2013 CDPedistas (see AUTHORS.txt)
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

"""Tests for the 'preprocesar' module."""

import os
import tempfile
import unittest

import config

from src.preproceso.preprocesar import PagesSelector



class PagesSelectorTestCase(unittest.TestCase):
    """Tests for the PagesSelector."""

    _dummy_processed = [
        ('arch1', 'dir1', 5, 3),  # 8
        ('arch2', 'dir2', 4, 3),  # 7
        ('arch3', 'dir3', 3, 2),  # 5
        ('arch4', 'dir4', 3, 1),  # 4
        ('arch5', 'dir5', 2, 2),  # 4
        ('arch6', 'dir6', 1, 1),  # 2
    ]

    def setUp(self):
        """Set up."""
        # write a dummy processed log
        fh, preproc_path = self._mktemp()
        fh.write("# Mandatory title\n")
        for data in self._dummy_processed:
            fh.write(config.SEPARADOR_COLUMNAS.join(map(str, data)) + '\n')
        fh.close()

        # get a temp for selected pages
        fh, chosen_path = self._mktemp()
        fh.close()

        # fix config to point to these files
        prv_preproc = config.LOG_PREPROCESADO
        config.LOG_PREPROCESADO = preproc_path
        self.addCleanup(setattr, config, 'LOG_PREPROCESADO', prv_preproc)
        prv_chosen = config.PAG_ELEGIDAS
        config.PAG_ELEGIDAS = chosen_path
        self.addCleanup(setattr, config, 'PAG_ELEGIDAS', prv_chosen)

        # fix config for version and page limit
        config.LIMITE_PAGINAS['version'] = 123

    def _mktemp(self):
        """Make a temporary file."""
        fd, path = tempfile.mkstemp()
        fh = os.fdopen(fd, 'wt')
        self.addCleanup(os.remove, path)
        return fh, path

    def test_assert_attributes_validity(self):
        """Need to first calculate for attribs be valid."""
        ps = PagesSelector()  # instantiate, and don't calculate
        self.assertRaises(ValueError, getattr, ps, 'top_pages')
        self.assertRaises(ValueError, getattr, ps, 'same_info_through_runs')

    def test_calculate_top_htmls_simple(self):
        """Calculate top htmls, simple version."""
        ps = PagesSelector()
        config.LIMITE_PAGINAS['version'] = 2
        ps.calculate('version')
        should_pages = [
            ('dir1', 'arch1', 8),
            ('dir2', 'arch2', 7),
        ]
        self.assertEqual(ps.top_pages, should_pages)

        # check info is stored ok in disk
        should_stored = [config.SEPARADOR_COLUMNAS.join(map(str, p)) + '\n'
                         for p in should_pages]
        with open(config.PAG_ELEGIDAS, 'rt') as fh:
            lines = fh.readlines()
        self.assertEqual(lines, should_stored)

    def test_calculate_top_htmls_complex(self):
        """Calculate top htmls, more complex.

        The page limit will cut the list in a page that has the same score of
        others, so let's include them all.
        """
        ps = PagesSelector()
        config.LIMITE_PAGINAS['version'] = 4
        ps.calculate('version')
        should_pages = [
            ('dir1', 'arch1', 8),
            ('dir2', 'arch2', 7),
            ('dir3', 'arch3', 5),
            ('dir4', 'arch4', 4),
            ('dir5', 'arch5', 4),
        ]
        self.assertEqual(ps.top_pages, should_pages)

        # check info is stored ok in disk
        should_stored = [config.SEPARADOR_COLUMNAS.join(map(str, p)) + '\n'
                         for p in should_pages]
        with open(config.PAG_ELEGIDAS, 'rt') as fh:
            lines = fh.readlines()
        self.assertEqual(lines, should_stored)

    def test_sameinfo_noprevious(self):
        """Check 'same info than before', no previous info."""
        os.remove(config.PAG_ELEGIDAS)
        ps = PagesSelector()
        ps.calculate('version')
        self.assertFalse(ps.same_info_through_runs)

    def test_sameinfo_previousdifferent(self):
        """Check 'same info than before', previous info there but different."""
        # make one pass just to write the 'choosen pages' file
        ps = PagesSelector()
        ps.calculate('version')

        # get that file and change it slightly
        with open(config.PAG_ELEGIDAS, 'rt') as fh:
            lines = fh.readlines()
        with open(config.PAG_ELEGIDAS, 'wt') as fh:
            fh.writelines(lines[:-1])

        # go again, the info will be the same
        ps = PagesSelector()
        ps.calculate('version')
        self.assertFalse(ps.same_info_through_runs)

    def test_sameinfo_previousequal(self):
        """Check 'same info than before', previous info there and equal."""
        # make one pass just to write the 'choosen pages' file
        ps = PagesSelector()
        ps.calculate('version')

        # go again, the info will be the same
        ps = PagesSelector()
        ps.calculate('version')
        self.assertTrue(ps.same_info_through_runs)
