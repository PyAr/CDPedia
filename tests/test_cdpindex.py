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

"""Tests for the cdpindex module."""

import config
from src.armado import cdpindex, to3dirs

import pytest


@pytest.fixture
def index(mocker):
    """Dummy index with a mocked 'create' method."""
    index = mocker.Mock(create=mocker.Mock())
    mocker.patch('src.armado.cdpindex.Index', index)
    return index


@pytest.fixture
def data(mocker, tmp_path):
    """Dummy data for building an index."""
    mocker.patch('config.LOG_TITLES', str(tmp_path / 'titles.txt'))
    mocker.patch('config.LOG_REDIRECTS', str(tmp_path / 'redirects.txt'))
    mocker.patch('config.DIR_INDICE', str(tmp_path / 'index'))
    # url and titles that should exist after preprocessing
    with open(config.LOG_TITLES, 'wt', encoding='utf-8') as fh:
        fh.write('foo|foo|\n')
        fh.write('bar|bar|\n')
        fh.write('baz|baz|\n')
    # redirections file must exist even if there's no redirection
    with open(config.LOG_REDIRECTS, 'wt') as fh:
        pass


@pytest.mark.parametrize('text_raw, text_norm', (
    ('FOO', 'foo'),
    ('FóÕ', 'foo'),
    ('ñandú', 'nandu'),
    ('.com', '.com'),
    ('AC/DC', 'ac/dc'),
    ('замо́к', 'замок'),
    ('παϊδάκια', 'παιδακια'),
))
def test_word_normalization(text_raw, text_norm):
    """Check lowercase convertion and diacritics removal."""
    assert text_norm == cdpindex.normalize_words(text_raw)


@pytest.mark.parametrize('fname_raw, words', (
    ('España´82', ['espana', '82']),
    ('España 82', ['espana', '82']),
    ('España_82', ['espana', '82']),
))
def test_filename_to_words(fname_raw, words):
    """Check getting words from the filename (used for redirects)."""
    assert cdpindex.filename2words(fname_raw) == words


def test_normal_entries_top_pages(index, data, mocker):
    """All entries from top_pages should be added to the index."""
    top_pages = [
        ('f/o/o', 'foo', 10),
        ('b/a/r', 'bar', 10),
        ('b/a/z', 'baz', 10),
    ]
    mocker.patch('src.preprocessing.preprocess.pages_selector', mocker.Mock(top_pages=top_pages))
    cdpindex.generate_from_html(None, None)
    assert index.create.call_count == 1
    # a generator of index entries was passed to the 'create' method but wasn't consumed
    entries_gen = index.create.call_args[0][1]
    assert len(list(entries_gen)) == len(top_pages)


def test_repeated_entries_top_pages(index, data, mocker):
    """Duplicated entries from top_pages should raise an exception."""
    top_pages = [
        ('f/o/o', 'foo', 10),
        ('b/a/r', 'bar', 10),
        ('f/o/o', 'foo', 10),
    ]
    mocker.patch('src.preprocessing.preprocess.pages_selector', mocker.Mock(top_pages=top_pages))
    cdpindex.generate_from_html(None, None)
    assert index.create.call_count == 1
    entries_gen = index.create.call_args[0][1]
    # duplicated entry should be detected while iterating over the entries generator
    with pytest.raises(KeyError):
        list(entries_gen)


def test_repeated_entry_redirects(index, data, mocker):
    """Don't add repeated redirect entries to the index."""
    with open(config.LOG_TITLES, 'wt', encoding='utf-8') as fh:
        fh.write('foo_bar|foo bar|\n')
    top_pages = [('f/o/o_bar', 'foo_bar', 10)]
    mocker.patch('src.preprocessing.preprocess.pages_selector', mocker.Mock(top_pages=top_pages))

    # these redirects will have similar titles after normalization, those will exact words
    # will be not included, only the one with the new word (and NOT the repeated one after that!)
    with open(config.LOG_REDIRECTS, 'wt', encoding='utf-8') as fh:
        fh.write('Foo Bar|foo_bar\n')
        fh.write('FOO BAR|foo_bar\n')
        fh.write('fOO bazzz|foo_bar\n')
        fh.write('BAZZZ fOo|foo_bar\n')
    cdpindex.generate_from_html(None, None)
    assert index.create.call_count == 1
    entries = list(index.create.call_args[0][1])

    # should have one entry from top_pages and one entry from redirects:
    #  - YES: the original article, for sure
    #  - NO: both next redirects, which after normalization have the same words
    #  - YES: the redirect bringing new words (note ALL words are indexed, not only the different
    #         ones, as all are needed if the user search for those words doing an AND)
    #  - NO: the last redirect, that again are the same words than an already indexed item
    assert len(entries) == 2
    words, _, (html, _, _, is_original, _) = entries[0]
    assert words == {'bar', 'foo'}
    assert html == 'f/o/o_bar/foo_bar'
    assert is_original
    words, _, (html, _, _, is_original, _) = entries[1]
    assert words == {'foo', 'bazzz'}
    assert html == 'f/o/o_bar/foo_bar'
    assert not is_original


def test_repeated_entry_redirects_special_madres(index, data, mocker):
    """Specific test for madres."""
    with open(config.LOG_TITLES, 'wt', encoding='utf-8') as fh:
        fh.write('Madres_de_Plaza_de_Mayo|Madres de Plaza de Mayo|\n')
    top_pages = [('M/a/dres_de_Plaza_de_Mayo', 'Madres_de_Plaza_de_Mayo', 10)]
    mocker.patch('src.preprocessing.preprocess.pages_selector', mocker.Mock(top_pages=top_pages))

    # these redirects will have similar titles after normalization, those will exact words
    # will be not included, only the one with the new word (and NOT the repeated one after that!)
    with open(config.LOG_REDIRECTS, 'wt', encoding='utf-8') as fh:
        fh.write('Madres|Madres_de_Plaza_de_Mayo\n')
    cdpindex.generate_from_html(None, None)
    assert index.create.call_count == 1
    entries = list(index.create.call_args[0][1])
    assert len(entries) == 2
    assert entries[0][0] == {'madres', 'de', 'plaza', 'mayo'}
    assert entries[1][0] == {'madres'}


@pytest.mark.parametrize('title', ('foo/bar', 'foo.bar', 'foo%bar'))
def test_redirects_with_special_chars(index, data, mocker, title):
    """Check redirects to pages containing encoded special filesystem chars."""
    # only target chars should be quoted: '/', '.' and '%'
    filename = to3dirs.to_filename(title)
    with open(config.LOG_TITLES, 'at', encoding='utf-8') as fh:
        fh.write('{}|{}|\n'.format(filename, title))
    top_pages = [('f/o/o', filename, 10)]
    mocker.patch('src.preprocessing.preprocess.pages_selector', mocker.Mock(top_pages=top_pages))
    with open(config.LOG_REDIRECTS, 'wt', encoding='utf-8') as fh:
        fh.write('redirect|{}\n'.format(title))

    cdpindex.generate_from_html(None, None)
    assert index.create.call_count == 1
    entries = list(index.create.call_args[0][1])
    assert len(entries) == 2


@pytest.mark.parametrize('title, expected_tokens', (
    ('Foo BAR', {'foo', 'bar'}),
    ('José de San Martín', {'jose', 'de', 'san', 'martin'}),
    ('Jeep Ñandú', {'jeep', 'nandu'}),
    ('Grañón (La Rioja)', {'granon', 'la', 'rioja'}),
    ('Chacarita (Buenos Aires)', {'chacarita', 'buenos', 'aires'}),
    ('Número π', {'numero', 'π'}),
    ('AC/DC', {'ac/dc', 'ac', 'dc'}),
    ('.com', {'.com', 'com'}),
    ('$9.99', {'$9.99', '99', '9'}),
    ('Fahrenheit 9/11', {'fahrenheit', '9/11', '9', '11'}),
    ('♥ Heart (álbum)', {'♥', 'heart', 'album'}),
    ('Србија', {'србија'}),
    ('Έλενα Παπαρίζου', {'ελενα', 'παπαριζου'}),
))
def test_title_tokenization(title, expected_tokens):
    """Check the tokens that will be inserted in the index."""
    tokens = set(cdpindex.tokenize_title(title))
    assert tokens == expected_tokens
