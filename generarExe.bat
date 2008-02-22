rem @echo off

python win32\pyinstaller-1.3\Makespec.py -D -a -c -o win32 -n CDPedia --icon=CDPedia.ico armado\main.py
python win32\pyinstaller-1.3\Build.py win32\CDPedia.spec
copy win32\distCDPedia\*.* salida\win32
