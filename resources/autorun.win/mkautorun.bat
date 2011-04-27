cd win32main
c:\python25\python.exe setup.py py2exe
cd ..
copy win32main\dist\*.* cdroot\cdpedia\win32\main
rem tools\mkisofs -v -V autorun -o demo.iso -R -J cdroot 
