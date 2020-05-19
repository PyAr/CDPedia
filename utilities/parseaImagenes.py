# -*- encoding: utf8 -*-

# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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
Muestra info del archivo comprimido.
"""

from __future__ import print_function

import sys
import os
sys.path.append(os.getcwd())
from src.imagenes import extraer  # NOQA import after path fix


def main(fname):
    pi = extraer.ParseaImagenes(test=True)
    pi.parsea(fname)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usar:  parseaImagenes.py <arch.html>")
        sys.exit()

    main(sys.argv[1])
