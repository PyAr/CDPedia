rem ajustar los paths antes de correr si fuese necesario
rem probablemente no funcione si los paths tienen espacios 

set python=c:\python27\python.exe
set pyinstaller2=D:\tmp\pyinstaller-2.0
set mini-iso=D:\tmp\cd_mini_3

SET old_cwd=%CD%

cd ..\..
rem actualizar imagen con el codigo y assets de la working copy donde estamos
%python% generar.py --update-mini %mini-iso%

rem generamos desde el dir de pyinstaller para no meter basura en la working copy
rem usamos --noupx porque algunos antivirus suelen marcar como sospechosos los
rem exes que usan esta compresion
cd /D %pyinstaller2% 
%python% pyinstaller.py  --onefile --noconsole --noupx  --icon=%old_cwd%\cdroot\cdpedia.ico %mini-iso%\cdpedia.py

rem %python% pyinstaller.py  --onefile --debug --noupx  --icon=%old_cwd%\cdroot\cdpedia.ico %mini-iso%\cdpedia.py

rem copiar el exe a la working copy y a la imagen de cdpedia
cd /D %old_cwd%
copy /B /Y %pyinstaller2%\cdpedia\dist\cdpedia.exe %mini-iso%\cdpedia.exe
copy /B /Y %pyinstaller2%\cdpedia\dist\cdpedia.exe cdroot\cdpedia.exe

rem tools\mkisofs -v -V autorun -o demo.iso -R -J cdroot 
