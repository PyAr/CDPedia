if not exist ..\..\..\..\cdroot\cdpedia\win32\main goto build
    rem limpiar
    rmdir /S /Q ..\..\..\..\cdroot\cdpedia\win32\main

:build
c:\python27\python.exe cxfreeze_debug_conf.py build -b ..\..\..\..\cdroot\cdpedia\win32\
ren ..\..\..\..\cdroot\cdpedia\win32\exe.win32-2.7 main

rem probablemente no queremos copiar las .dll del MS C runtime en la working copy
rem asi que las comento afuera (rem). Se puede hacer la copia hacia la mini-imagen
rem para poder testear, llegado el caso.

rem copiando dlls que python necesita
rem copy /B /Y C:\WINDOWS\WinSxS\Manifests\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375.manifest ..\..\..\..\cdroot\cdpedia\win32\main\*.*

rem copy /B /Y C:\WINDOWS\WinSxS\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375\msvcm90.dll ..\..\..\..\cdroot\cdpedia\win32\main\*.*

rem copy /B /Y C:\WINDOWS\WinSxS\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375\msvcp90.dll ..\..\..\..\cdroot\cdpedia\win32\main\*.*

rem copy /B /Y C:\WINDOWS\WinSxS\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375\msvcr90.dll ..\..\..\..\cdroot\cdpedia\win32\main\*.*
