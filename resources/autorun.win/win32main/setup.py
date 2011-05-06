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
			"encodings", "encodings.*",
        ],
		"packages": ["win32api", "encodings"]
    }
}

setup(windows=["win32main.py"], console=["console.py"], options=opts)