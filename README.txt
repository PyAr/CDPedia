Creación de la imagen
---------------------

1. Bajar el dump estático en español que está en http://static.wikipedia.org/
  descomprimirlo así: 7z x wikipedia-es-html.tar.7z -so | tar -x
  El espacio que hay que tener para poder descomprimir es aprox. 20GB el de junio 
  de 2008, seguramente si hay uno mas nuevo sea mas grande.

2. Crear un directorio fuente (por ejemplo, "fuentes"), y poner ahí los 
   archivos del dump estático que querramos usar (adentro del dir 'articles',
   más los siguientes directorios obligatorios:
     
      - misc
      - raw
      - skins

3. Ejecutar el "generar.py"

4. Disfrutar del archivo final "cdpedia.iso"


Prueba de los sistemas
----------------------

1. Ejecutar main.py
