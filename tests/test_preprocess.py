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

"""Tests for the 'preprocess' module."""

import codecs
import logging
import os

import config
from src.preprocessing import preprocess
from src.preprocessing.preprocessors import SCORE_PEISHRANC

import pytest


class TestWikiFile(object):
    """Tests for WikiFile."""

    @pytest.fixture
    def wikifile(self, mocker, tmp_path):
        """Create a test WikiFile."""
        mocker.patch('config.DIR_PREPROCESADO', str(tmp_path))
        return preprocess.WikiFile

    @pytest.fixture
    def article(self, tmp_path):
        """Dummy article within required directory structure."""
        root = str(tmp_path)
        file_name = 'fooarticle'
        last3dirs = os.path.sep.join(file_name[:3])
        cwd = os.path.join(root, last3dirs)
        os.makedirs(cwd)
        with codecs.open(os.path.join(cwd, file_name), 'w', encoding='utf-8') as fh:
            fh.write('<html><body><p>fooarticle content</p></body></html>')
        return cwd, last3dirs, file_name

    def test_init(self, wikifile):
        root = 'rootdir'
        file_name = 'fooarticle'
        last3dirs = os.path.sep.join(file_name[:3])
        cwd = os.path.join(root, last3dirs)
        wf = wikifile(cwd, last3dirs, file_name)
        assert wf.relative_path == os.path.join(last3dirs, file_name)
        assert wf._filename == os.path.join(root, last3dirs, file_name)

    def test_soup(self, article, wikifile):
        """Test soup creation."""
        wf = wikifile(*article)
        assert wf.soup.find('p') is not None

    def test_length(self, article, wikifile):
        """Test html length."""
        cwd, last3dirs, file_name = article
        wf = wikifile(cwd, last3dirs, file_name)
        length = os.stat(os.path.join(cwd, file_name)).st_size
        assert length == wf.original_html_length

    def test_str(self, article, wikifile):
        """Test string representation."""
        wf = wikifile(*article)
        assert str(wf) == '<WikiFile: fooarticle>'

    def test_save(self, article, wikifile):
        """Test correct save of processed article."""
        cwd, last3dirs, file_name = article
        wf = wikifile(cwd, last3dirs, file_name)
        wf.soup  # load content
        wf.save()
        with codecs.open(os.path.join(cwd, file_name), 'r', encoding='utf-8') as fh:
            assert 'fooarticle content' in fh.read()


class TestWikiSite(object):
    """Tests for WikiSite."""

    @pytest.fixture
    def wikisite(self, mocker, tmp_path):
        """Create a test WikiSite."""
        target = 'src.preprocessing.preprocess.'
        mocker.patch(target + 'LOG_SCORES_ACCUM', str(tmp_path / 'accum'))
        mocker.patch(target + 'LOG_SCORES_FINAL', str(tmp_path / 'final'))
        mocker.patch('config.LOG_TITLES', str(tmp_path / 'titles'))
        mocker.patch('config.LOG_REDIRECTS', str(tmp_path / 'redir'))
        mocker.patch('config.LOG_PREPROCESADO', str(tmp_path / 'prepr.log'))
        mocker.patch('config.DIR_PREPROCESADO', str(tmp_path / 'prepr'))
        mocker.patch('config.langconf', create=True)
        mocker.patch(target + 'WikiFile', preprocess.WikiFile)

        # set up the portal pages in a custom dir_assets
        mocker.patch('config.DIR_ASSETS', str(tmp_path))
        portals_file = tmp_path / 'dynamic' / 'portal_pages.txt'
        portals_file.parent.mkdir(exist_ok=True)
        portals_file.touch()

        return preprocess.WikiSite

    @pytest.fixture
    def articles(self, tmp_path):
        """Fake scraped articles with expected scores."""
        # create articles
        root = str(tmp_path)
        titles = 'eggs', 'bacon', 'ham', 'spam'
        content = '<html><body><a href="/wiki/spam">spam</a></body></html>'
        for title in titles:
            d = os.path.join(root, *title[:3])
            os.makedirs(d)
            with codecs.open(os.path.join(d, title), 'w', encoding='utf-8') as fh:
                fh.write(content)

        # compute expected scores
        def _join(*args):
            return config.SEPARADOR_COLUMNAS.join(str(a) for a in args)

        ln = len(content)
        real = [_join(t, 'R', ln) for t in titles]
        n_extra = len(titles) - 1
        extra = [_join('spam', 'E', SCORE_PEISHRANC)] * n_extra
        final = [_join(t, ln) for t in titles[:-1]]
        final.append(_join('spam', ln + n_extra * SCORE_PEISHRANC))
        scores = dict(accum=sorted(real + extra), final=set(final))

        return root, set(titles), scores

    def test_log(self, articles, wikisite):
        """Test file log."""
        root, titles, _ = articles
        ws = wikisite(root)
        ws.process()
        with codecs.open(config.LOG_PREPROCESADO, 'r', encoding='utf-8') as fh:
            titles_proc = set(fh.read().split())
        assert titles_proc == titles

    def test_scores_accum(self, articles, wikisite):
        """Test saved accumulated scores."""
        root, titles, scores = articles
        ws = wikisite(root)
        ws.process()
        with codecs.open(preprocess.LOG_SCORES_ACCUM, 'r', encoding='utf-8') as fh:
            scores_accum = sorted(fh.read().split())
        assert scores_accum == scores['accum']

    def test_scores_final(self, articles, wikisite):
        """Test saved final scores."""
        root, _, scores = articles
        ws = wikisite(root)
        ws.process()
        ws.commit()
        with codecs.open(preprocess.LOG_SCORES_FINAL, 'r', encoding='utf-8') as fh:
            scores_final = set(fh.read().split())
        assert scores_final == scores['final']

    def test_discard_none_score(self, articles, wikisite, mocker):
        """Discard article if score is None."""
        root, _, _ = articles
        ws = wikisite(root)
        ws.preprocessors = [mocker.Mock(return_value=(None, []))]
        ws.process()
        ws.commit()
        assert os.path.getsize(preprocess.LOG_SCORES_ACCUM) == 0

    def test_discard_no_3dirs(self, tmp_path, wikisite):
        """Content inside no-3dirs must be discarded."""
        with (tmp_path / 'spam').open('wt') as fh:
            fh.write('spam')
        ws = wikisite(str(tmp_path))
        ws.process()
        assert os.path.getsize(config.LOG_PREPROCESADO) == 0

    def test_processed_before(self, articles, wikisite):
        """Don't process titles logged as processed."""
        root, titles, _ = articles
        with codecs.open(config.LOG_PREPROCESADO, 'w', encoding='utf-8') as fh:
            fh.write('ham\n')
        ws = wikisite(root)
        ws.process()
        with codecs.open(config.LOG_PREPROCESADO, 'r', encoding='utf-8') as fh:
            titles_proc = set(s.strip() for s in fh)
        assert len(titles_proc) == len(titles)
        assert titles_proc == titles

    def test_empty_dir(self, tmp_path, wikisite):
        """Test processing of empty root dir."""
        ws = wikisite(str(tmp_path))
        ws.process()
        ws.commit()
        assert os.path.getsize(config.LOG_PREPROCESADO) == 0


class TestPagesSelector(object):
    """Tests for the PagesSelector"""

    @pytest.fixture
    def scores(self, mocker, tmp_path):
        """Fake final scores file."""
        target = 'src.preprocessing.preprocess.LOG_SCORES_FINAL'
        mocker.patch(target, str(tmp_path / 'final'))
        pages = [
            ('fooarch1', 8),
            ('bararch2', 7),
            ('fooarch3', 5),
            ('bararch4', 4),
            ('fooarch5', 4),
            ('bararch6', 2),
        ]
        lines = (config.SEPARADOR_COLUMNAS.join((p, str(v))) for (p, v) in pages)
        with codecs.open(preprocess.LOG_SCORES_FINAL, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines))

    @pytest.fixture
    def pages_selector(self, mocker, tmp_path, scores):
        """Create a test PagesSelector."""
        mocker.patch('config.PAG_ELEGIDAS', str(tmp_path / 'chosen'))
        mocker.patch('config.imageconf', dict(page_limit=123))  # mock dynamic data
        return preprocess.PagesSelector

    def test_assert_attributes_validity(self, pages_selector):
        """Need to first calculate for attribs to be valid."""
        ps = pages_selector()
        with pytest.raises(ValueError):
            getattr(ps, 'top_pages')
            getattr(ps, 'same_info_through_runs')

    def test_calculate_top_htmls_simple(self, pages_selector):
        """Calculate top htmls, simple version."""
        config.imageconf['page_limit'] = 2
        ps = pages_selector()
        ps.calculate()
        should_pages = [
            ('f/o/o', 'fooarch1', 8),
            ('b/a/r', 'bararch2', 7),
        ]
        assert ps.top_pages == should_pages

        # check info is stored ok in disk
        should_stored = [config.SEPARADOR_COLUMNAS.join(map(str, p)) + '\n'
                         for p in should_pages]
        with open(config.PAG_ELEGIDAS, 'r', encoding="utf-8") as fh:
            lines = fh.readlines()
        assert lines == should_stored

    def test_calculate_top_htmls_complex(self, pages_selector):
        """Calculate top htmls, more complex.

        The page limit will cut the list in a page that has the same score of
        others, so let's include them all.
        """
        config.imageconf['page_limit'] = 4
        ps = pages_selector()
        ps.calculate()
        should_pages = [
            ('f/o/o', 'fooarch1', 8),
            ('b/a/r', 'bararch2', 7),
            ('f/o/o', 'fooarch3', 5),
            ('b/a/r', 'bararch4', 4),
            ('f/o/o', 'fooarch5', 4),
        ]
        assert ps.top_pages == should_pages

        # check info is stored ok in disk
        should_stored = [config.SEPARADOR_COLUMNAS.join(map(str, p)) + '\n'
                         for p in should_pages]
        with open(config.PAG_ELEGIDAS, 'r', encoding="utf-8") as fh:
            lines = fh.readlines()
        assert lines == should_stored

    def test_sameinfo_noprevious(self, pages_selector):
        """Check 'same info than before', no previous info."""
        ps = pages_selector()
        ps.calculate()
        os.remove(config.PAG_ELEGIDAS)
        ps.calculate()
        assert not ps.same_info_through_runs

    def test_sameinfo_previousdifferent(self, pages_selector):
        """Check 'same info than before', previous info there but different."""
        # make one pass just to write the 'choosen pages' file
        ps = pages_selector()
        ps.calculate()

        # get that file and change it slightly
        with codecs.open(config.PAG_ELEGIDAS, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
        with codecs.open(config.PAG_ELEGIDAS, 'w', encoding='utf-8') as fh:
            fh.writelines(lines[:-1])

        # go again, the info won't be the same
        ps = pages_selector()
        ps.calculate()
        assert not ps.same_info_through_runs

    def test_sameinfo_previousequal(self, pages_selector):
        """Check 'same info than before', previous info there and equal."""
        # make one pass just to write the 'choosen pages' file
        ps = pages_selector()
        ps.calculate()

        # go again, the info will be the same
        ps = pages_selector()
        ps.calculate()
        assert ps.same_info_through_runs


class TestRun(object):
    """Tests for the `run` function."""

    def test_skip(self, mocker, caplog):
        mocker.patch('os.path.exists', mocker.Mock(return_value=True))
        """Skip preprocessing if final scores file exists."""
        with caplog.at_level(logging.INFO):
            preprocess.run('foo')
        assert 'Skipping the whole processing stage' in caplog.text

    def test_run(self, mocker):
        """Start articles preprocessing."""
        mocker.patch('os.path.exists', mocker.Mock(return_value=False))
        m = mocker.MagicMock()
        mocker.patch('src.preprocessing.preprocess.WikiSite', m)
        preprocess.run('foo')
        m.assert_has_calls((mocker.call().process(), mocker.call().commit()))
