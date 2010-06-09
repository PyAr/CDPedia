from distutils.core import setup
import py2exe

opts = {
    "py2exe": {
        "skip_archive": False,
        "excludes": [
            "_ssl",
            "doctest",
            "pdb",
            "dis",
            "email"
        ],
        "includes": [ 
            "webbrowser",
            "BaseHTTPServer",
            "cgi",
            "urllib2",
            "shutil",
        ],
		"packages": ["win32api"]
    }
}

setup(windows=["win32main.py"], options=opts)