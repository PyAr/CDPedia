Creación de la imagen
---------------------

1. Hacer un dump con el scraper y descomprimirlo en algún lado.

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


Prueba de los sistemas
----------------------

1. Ejecutar main.py
