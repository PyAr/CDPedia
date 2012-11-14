"""
Configuracion cxfreeze para obtener binarios windows.
Esta version es sin consola, seria para release.
Para testeo conviene usar el build con consola.
"""

from cx_Freeze import setup
from cx_Freeze import Executable

exe = Executable(
        script=r"win32main.py",
        base="Win32GUI",

        compress = True,
        copyDependentFiles = True,
        appendScriptToExe = False,
        appendScriptToLibrary = False,
)

extra_options = {
    "packages": ["werkzeug"],
    "optimize" : 2,
    "compressed":True,
}

setup(
    name="cdpedia",
    version="0.1",
    options = {"build_exe": extra_options},
    description="CDpedia, la wikipedia en CD / DVD",
    executables=[exe],
)
