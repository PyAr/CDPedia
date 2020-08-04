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

"""Helpers for managing localizations

Script usage: `python localize.py [lang]`:

- python localize.py           # Show status of all languages
- python localize.py pt        # Build portuguese translation

"""

import argparse
import logging
import os
import tempfile

from babel import localedata
from babel.messages.frontend import CommandLineInterface
from babel.messages.pofile import read_po

logger = logging.getLogger('localize')

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALE_DIR = os.path.join(ROOT_DIR, 'locale')
SOURCE_DIR = os.path.join(ROOT_DIR, 'src', 'web')


def translation_status(lang):
    """Check status of given language translation."""
    loc = _LocaleManager(lang, LOCALE_DIR, SOURCE_DIR)
    loc.check_template()
    complete, updated = loc.status()
    compiled = os.path.isfile(loc.mo_file)
    return updated, complete, compiled


class _LocaleManager:
    """Manage localizations."""

    def __init__(self, lang, locale_dir, source_dir):
        self.lang = lang
        self.locale_dir = locale_dir
        self.source_dir = source_dir
        self.config = os.path.join(locale_dir, 'babel.config')
        self.po_template = os.path.join(locale_dir, 'core.pot')
        self.po_file = os.path.join(locale_dir, '{}.po'.format(lang)) if lang else None
        self.mo_file = os.path.join(locale_dir, lang, 'LC_MESSAGES', 'core.mo') if lang else None
        self.source_messages = None  # current number of messages in sources
        self.template_updated = None  # if template messages match sources messages

    def _run(self, *params):
        """Run a pybabel command."""
        cmd = ['pybabel', '-q'] + list(params)
        CommandLineInterface().run(cmd)

    def extract(self, output=None):
        """Extract messages from sources to .pot file."""
        if output is None:
            output = self.po_template
        self._run('extract', '-F', self.config, '-o', output, '--project', 'CDPedia',
                  '--copyright-holder', 'CDPedistas (see AUTHORS.txt)', self.source_dir)

    def init(self):
        """Create .po language file from .pot template, overwrite it if it exists."""
        if not localedata.exists(self.lang):
            # workaround for missing locale in babel package
            localedata._cache[self.lang] = {}
        self._run('init', '-l', self.lang, '-i', self.po_template, '-o', self.po_file)

    def update(self):
        """Update exising .po language file from .pot template."""
        self._run('update', '-l', self.lang, '-i', self.po_template, '-o', self.po_file)

    def compile(self):
        """Create .mo file from .po file for current language."""
        # output = os.path.join(self.locale_dir, self.lang, 'LC_MESSAGES', 'core.mo')
        os.makedirs(os.path.dirname(self.mo_file), exist_ok=True)
        self._run('compile', '-l', self.lang, '-i', self.po_file, '-o', self.mo_file)

    @staticmethod
    def get_messages(filepath, lang=None):
        """Get original messages from po/pot file."""
        with open(filepath, 'rb') as fh:
            catalog = read_po(fh, lang)
        # id is the original string, first one is always empty (used for mime_headers)
        return [m.id for m in catalog][1:]

    def check_template(self):
        """Check if messages in sources and template are the same."""
        # get messages from last generated template
        messages_old = self.get_messages(self.po_template)

        # extract messages from sources
        _, filepath = tempfile.mkstemp()
        self.extract(output=filepath)
        messages_new = self.get_messages(filepath)
        os.remove(filepath)

        self.source_messages = len(messages_new)
        self.template_updated = messages_old == messages_new
        logger.info('Messages: %d in sources, %d in template, up to date: %s',
                    len(messages_new), len(messages_old), self.template_updated)

    def get_completion(self):
        """Get completion percentage of current language translation."""
        with open(self.po_file, 'rb') as fh:
            catalog = read_po(fh, self.lang)
        original = len(catalog)
        translated = 0
        # first catalog message is always empty
        for message in list(catalog)[1:]:
            if message.string:
                translated += 1
        percentage = 0
        if original:
            percentage = translated * 100 // original
        return original, translated, percentage

    def status(self):
        """Check translation status of current language."""
        original, translated, percentage = self.get_completion()
        complete = percentage == 100

        if self.template_updated is True:
            if complete:
                if translated == self.source_messages:
                    status = 'ok!'
                else:
                    # Missing messages in language file
                    status = 'outdated'
            else:
                status = 'incomplete'
        elif self.template_updated is False:
            # language file outdated no matter completion percentage
            status = 'outdated'
        else:
            status = 'unchecked'  # template not checked

        logger.info('Language %s %3d%% translated (%2d of %d messages)\t> %s',
                    self.lang.upper(), percentage, translated, original, status.upper())

        return complete, self.template_updated

    def stats(self):
        """Show stats of all current translations."""
        for filename in sorted(os.listdir(self.locale_dir)):
            lang, ext = os.path.splitext(filename)
            if ext == '.po':
                self.lang = lang
                self.po_file = os.path.join(self.locale_dir, filename)
                self.status()


def _localize(lang=None):
    """Update/add translation for given language."""
    loc = _LocaleManager(lang, LOCALE_DIR, SOURCE_DIR)
    if lang is not None:
        # extract, update and compile messages for given language
        logger.info('Building messages for %s language', lang.upper())
        loc.extract()
        loc.check_template()
        if os.path.isfile(loc.po_file):
            loc.update()
        else:
            loc.init()
        loc.compile()
        loc.status()
    else:
        # show stats for template and all available languages
        loc.check_template()
        loc.stats()


if __name__ == '__main__':

    logging.basicConfig(format='%(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser(description='Manage CDPedia localizations')
    parser.add_argument('language', nargs='?', default=None, help='Target localization language')

    args = parser.parse_args()
    _localize(args.language)
