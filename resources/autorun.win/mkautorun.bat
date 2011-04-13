cd win32main
python setup.py py2exe
cd ..
copy win32main\dist\*.* cdroot\cdpedia\win32\main
rem tools\mkisofs -v -V autorun -o demo.iso -R -J cdroot 
