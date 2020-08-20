======
README
======

This directory contains instructions and necesary files to:

1. Embed python in CDPedia image to allow its use on Windows without a python installation.
2. Make CDPedia start automatically when inserting the CD/DVD, if autorun is enabled.


Embedding python
================

Download latest python embedable `.zip` distribution:

    cd resources/autrun.win
    wget https://www.python.org/ftp/python/3.8.5/python-3.8.5-embed-win32.zip

When generating a CDPedia release, the contents of this archive will be extracted to the
`python` directory of the image. To start up CDPedia on Windows use a `cdpedia.bat` file
in image root with the following command:

    start "CDPedia" "python\pythonw.exe" "cdpedia.py"


Compatibility
-------------

This python distribution will run on machines with the Universal C Runtime (UCRT) component,
which is normally installed through updates in Windows Vista, 7 and 8.1, and is a system
component of Windows 10. Offline installers for each platform can be downloaded from
https://support.microsoft.com/en-us/help/3118401/update-for-universal-c-runtime-in-windows


Autorun
=======

Include a file with special name ``autorun.inf`` in CD/DVD root to tell Windows what
command to run and what icon to show when disk is inserted.


Testing
=======

Generate a CDPedia image in Linux. Test it on Windows by double-clicking `cdpedia.bat`.
If web browser doesn't open after a few seconds, an error may have occurred. In this case,
open a terminal and run this command to analyze its output:

    cd path\to\cdpedia-image
    python\python.exe cdpedia.py
