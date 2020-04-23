#!/usr/bin/env python

# Copyright 2013-2020 CDPedistas (see AUTHORS.txt)
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
from src.preproceso import preprocesar


class PagesSelectorTestCase(unittest.TestCase):
    """Tests for the PagesSelector."""

    _dummy_processed = [
        ('fooarch1', 'f/o/o', 5, 3),  # 8
        ('bararch2', 'b/a/r', 4, 3),  # 7
        ('fooarch3', 'f/o/o', 3, 2),  # 5
        ('bararch4', 'b/a/r', 3, 1),  # 4
        ('fooarch5', 'f/o/o', 2, 2),  # 4
        ('bararch6', 'b/a/r', 1, 1),  # 2
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
        config.imageconf = dict(page_limit=123)

        # log scores
        fh, path = self._mktemp()
        for arch, _, v1, v2 in self._dummy_processed:
            fh.write(config.SEPARADOR_COLUMNAS.join((arch, str(v1 + v2))) + '\n')
        fh.close()
        prv_log_preprocesado = preprocesar.LOG_SCORES_FINAL
        preprocesar.LOG_SCORES_FINAL = path
        self.addCleanup(setattr, preprocesar, 'LOG_SCORES_FINAL', prv_log_preprocesado)

    def _mktemp(self):
        """Make a temporary file."""
        fd, path = tempfile.mkstemp()
        fh = os.fdopen(fd, 'wt')
        self.addCleanup(os.remove, path)
        return fh, path

    def test_assert_attributes_validity(self):
        """Need to first calculate for attribs be valid."""
        ps = preprocesar.PagesSelector()  # instantiate, and don't calculate
        self.assertRaises(ValueError, getattr, ps, 'top_pages')
        self.assertRaises(ValueError, getattr, ps, 'same_info_through_runs')

    def test_calculate_top_htmls_simple(self):
        """Calculate top htmls, simple version."""
        ps = preprocesar.PagesSelector()
        config.imageconf['page_limit'] = 2
        ps.calculate()
        should_pages = [
            ('f/o/o', 'fooarch1', 8),
            ('b/a/r', 'bararch2', 7),
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
        ps = preprocesar.PagesSelector()
        config.imageconf['page_limit'] = 4
        ps.calculate()
        should_pages = [
            ('f/o/o', 'fooarch1', 8),
            ('b/a/r', 'bararch2', 7),
            ('f/o/o', 'fooarch3', 5),
            ('b/a/r', 'bararch4', 4),
            ('f/o/o', 'fooarch5', 4),
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
        ps = preprocesar.PagesSelector()
        ps.calculate()
        self.assertFalse(ps.same_info_through_runs)

    def test_sameinfo_previousdifferent(self):
        """Check 'same info than before', previous info there but different."""
        # make one pass just to write the 'choosen pages' file
        ps = preprocesar.PagesSelector()
        ps.calculate()

        # get that file and change it slightly
        with open(config.PAG_ELEGIDAS, 'rt') as fh:
            lines = fh.readlines()
        with open(config.PAG_ELEGIDAS, 'wt') as fh:
            fh.writelines(lines[:-1])

        # go again, the info will be the same
        ps = preprocesar.PagesSelector()
        ps.calculate()
        self.assertFalse(ps.same_info_through_runs)

    def test_sameinfo_previousequal(self):
        """Check 'same info than before', previous info there and equal."""
        # make one pass just to write the 'choosen pages' file
        ps = preprocesar.PagesSelector()
        ps.calculate()

        # go again, the info will be the same
        ps = preprocesar.PagesSelector()
        ps.calculate()
        self.assertTrue(ps.same_info_through_runs)
