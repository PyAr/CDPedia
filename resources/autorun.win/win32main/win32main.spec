# -*- mode: python -*-
import os
cdpedia_path = os.path.join('..', '..', '..')

# Agregamos a cdpedia.py como un script para que analize y busque dependencias
# de bibliotecas de la stdlib. Pero como tambien agrega los archivos fuente
# de la cdpedia misma que no queremos que queden dentro del .exe los sacamos.

a = Analysis([os.path.join(HOMEPATH, 'support\\_mountzlib.py'), 
              os.path.join(HOMEPATH, 'support\\useUnicode.py'), 
              'win32main.py', os.path.join(cdpedia_path, 'cdpedia.py')])

# Listado de los modulos de la cdpedia (empiezan con 'src')
a_cdpedia_pure = [module for module in a.pure if module[0].startswith("src")]
cdpedia_pure = a_cdpedia_pure + [("cdpedia","",""), ("config","","")]

# Quitamos los modulos de la cdpedia
a.pure = a.pure - cdpedia_pure

# Quitamos el script cdpedia.py del .exe
a.scripts = a.scripts - [('cdpedia','','')]

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('..', 'cdroot\cdpedia\win32\main\win32main.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=False)
