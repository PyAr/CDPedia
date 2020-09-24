En mi blog comenté sobre la este proyecto [1], y en el sexto comentario apuntaron a unos parsers de terceros para pasar de XML a HTML.

Si uno pudiera tener un xml2html.py que armara el HTML a mostrar al usuario a partir del XML original, los volúmenes de datos a manejar en todas las etapas del proyecto serían bastante menores.

Me alegré bastante cuando encontré mwlib [2], una biblioteca hecha en Python para parsear los artículos XML y generar el HTML. El primer día de trabajo en PyCamp 2008 lo pasé tratando de usar esto.

El XML que publica Wikimedia, con sólo los artículos, templates y etcéteras en la última versión (y no todas las discusiones, ni todo el historial) pesa 1.7GB, con lo cual era imposible abrir el XML con herramientas de fácil uso como ElementTree. Pero Chipaca hizo un parseador en SAX (que va recorriendo el XML gradualmente, y no tiene que cargarlo entero en memoria), que yo luego modifiqué un poco y dejé en /articleExtractor.py/.

Ya pudiendo separar el artículo, me puse a jugar con la biblioteca mwlib en si, para convertirlo a HTML. Acá me encontré con algunas sorpresas, pero luego de hacer algunos análisis durante un par de horas, las pudimos descartar. 

Una era que teníamos la dependencia de /latex/, para transformar texto en formato MAthML en una imágen con la fórmula matemática en si. Vimos sin embargo que en el XML teníamos el MathML, y como Firefox es capaz en sí de parsear esto y mostrarlo como corresponde, decidimos que no era un problema.

El otro punto era la dependencia en /PIL/, la biblioteca de manejo de imágenes de Python. Como el tratamiento de las imágenes, qué incluir y cómo era todo un tema aparte, decidimos no preocuparnos acá hasta que llegue el momento.

Y finalmente, teníamos una dependencia de /perl/, para crear unas imágenes de linea de tiempo. Tuute estuvo buscando un montón y realmente apenas hay de estas imágenes en la wikipedia en español. Encima, la utilización de esta capacidad en la biblioteca está complicada, porque necesita usar unos directorios en particular, y cosas así. Entonces, decidimos "tocar" la biblioteca para que directamente no use esto.

Finalmente, entonces, éramos capaces de traducir el XML a HTML. El proceso es bien simple, si se fijan el código de /xml2html.py/ es bastante simple. ¡Y genera un HTML bastante piola! Sin embargo, dá algunos errores y me puse a ver qué pasaba.

Una de los primeros detalles es que no encontraba algunas categorías. Y esto era porque en el XML, al ser en español, están los tags como "categoría", y no como "category". Luego de revisar durante un buen rato como cambiarle el locale al parser antes de laburar, encontré que esto estaba bastante chancho: están hardcodeados en los programas estos tags para inglés y alemán, pero nada más. Feo, sucio. Pero agregué algunos en castellano y seguí experimentando. El HTML ahora se parecía más al original.

Otro gran detalle es que no encontraba unos templates. Nuevamente con la ayuda de tuute, encontramos que los templates están en el .xml grandote que teníamos: el template otrosusos era un artículo allí llamado "Plantilla:Otrosusos" (nótese el cambio de minúscula a mayúscula).

Acá me di cuenta que para más o menos poder seguir generando la info, tendríamos que extraer estas Plantillas de forma previa, para poder alimentársela al parser. Como el parser y el resto están preparados para conectarse a una base de datos como la de wikipedia, había que: o generar una base de datos similar, o seguir tocando la biblioteca para que acepte las cosas de otra forma.

En el mismo proceso, actualicé el archivo xml, ya que antes de venir para acá había bajado la última versión pero por error seguía usando la versión anterior. Y aparecieron nuevas categorías, lo que implicaría seguir modificando la mwlib a mano, :(.

En función de todos estos drawbacks y dependencias, entendimos que no podríamos pasar de XML a HTML en el momento de servirlos, en la máquina del usuario final, sino que podíamos generar una especie de htmls reducidos y más simples, de manera de procesar y guardar HTMLS de forma similar a la idea original del proyecto, pero con volúmenes más simples.

Pero luego, viendo como iba creciendo el HTML que estábamos generando, que todavía faltaba incorporarle los templates, y considerando los tamaños relativos con respecto a los HTMLs estáticos que la misma Wikipedia genera (y que eran la fuente de datos originalmente).

Entonces, luego de analizarlo, con Alecu y Tuute decidimos que este camino no implicaba mayor desarrollo, y lo dimos de baja.

[1] http://www.taniquetil.com.ar/plog/post/1/323
[2] http://code.pediapress.com/wiki/wiki/mwlib 
