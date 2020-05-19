# Copyright 2008-2020 CDPedistas (see AUTHORS.txt)
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

from __future__ import print_function

import codecs
import sys
import xml.sax

usage = """Usar: %s [-x] filename title outfile

-x significa "exacto"
"""


class Handler(xml.sax.handler.ContentHandler):
    in_page = False
    in_title = False
    this_page = False
    in_this_text = False

    def __init__(self, exacto, wanted, out):
        self.wanted = wanted
        self.accum_title = ""
        self.out = out
        self.exacto = exacto

    def startElement(self, name, attrs):
        if name == 'page':
            self.in_page = True
        if self.in_page and name == 'title':
            self.in_title = True
        if self.this_page and name == "text":
            self.in_this_text = True

    def endElement(self, name):
        if name == 'page':
            self.in_page = False
            self.this_page = False
        if self.in_page and name == 'title':
            self.in_title = False
            if self.exacto:
                if self.wanted == self.accum_title:
                    print(self.accum_title)
                    self.this_page = True
            else:
                if self.wanted in self.accum_title:
                    print(self.accum_title)
                    self.this_page = True
            self.accum_title = ""
        if name == "text":
            self.in_this_text = False

    def characters(self, content):
        if self.in_title:
            self.accum_title += content
            return
        if self.in_this_text:
            self.out.write(content)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(usage % sys.argv[0])
        sys.exit(1)

    exacto = False
    if sys.argv[1] == "-x":
        exacto = True
        del sys.argv[1]

    filename = sys.argv[1]
    wanted = sys.argv[2].decode("utf8")
    arch = codecs.open(sys.argv[3], "w", "utf8")
    h = Handler(exacto, wanted, arch)
    xml.sax.parse(filename, h)
