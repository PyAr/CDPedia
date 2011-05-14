Creación de la imagen
---------------------

1. Bajar el último `dump <http://pyar.usla.org.ar/eswiki_dump_20110219.tar.7z>`_
   y descomprimirlo en algún lado (7z x -so eswiki_dump_20110219.tar.7z |tar x).
   También revisar los "Términos de uso", a ver si cambiaron (ver en
   utilities/como_hacer_un_dump.txt)


2. Crear un directorio fuente (por ejemplo, "fuentes"), y poner ahí los
   archivos del dump estático que querramos usar (en un dir 'articles'),
   más algunos directorios con data estática:

     mkdir fuentes
     cd fuentes
     ln -s /discogrande/articulos articles
     ln -s ../resources/static/misc .
     ln -s ../resources/static/skins .

3. Ejecutar el "generar.py"

     python generar.py fuentes


4. Disfrutar del archivo final "cdpedia.iso"

Para desarrolladores
--------------------

Si lo que se desea es hacer pruebas y mejoras al código de cdpedia, se cuenta
con un dump para desarrollo.
Se debe descargar `dump-dev <http://pyar.usla.org.ar/eswiki_dump_20110219-dev.tar.gz>`_
Y crear los links para ''misc'' y ''skins''

Prueba de los sistemas
----------------------

1. Ejecutar main.py
