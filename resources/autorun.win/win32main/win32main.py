#!/usr/bin/env python

import sys
import os
import win32api
sys.path.append(".")

# para que py2exe no trate de crear un logfile en el CD
sys.stderr = open(os.devnull, "w")

# para que windows no muestre "no disk in the drive"
olderror = win32api.SetErrorMode(1)

import main