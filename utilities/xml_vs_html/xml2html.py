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
sys.path.append("/data/test")
from mwlib import htmlwriter, uparser, dummydb  # NOQA import after fixing path


def main(titulo, archin, archout):
    out = codecs.open(archout, "w", "utf8")

    inp = codecs.open(archin, "r", "utf8")
    article = inp.read()
    inp.close()

    p = uparser.parseString(titulo, raw=article, wikidb=dummydb.DummyDB())

    w = htmlwriter.HTMLWriter(out)
    w.write(p)
    out.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usar  %s titulo input.xml output.html" % sys.argv[0])
        sys.exit()
    main(*sys.argv[1:])
