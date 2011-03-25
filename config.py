# -*- coding: utf-8 -*-

# Ubicación de los archivos estáticos online
# Debe tener la barra al final
URL_WIKIPEDIA = "http://download.wikimedia.org/static/"
IDIOMA = "es"

# info para el compresor / decompresor
ARTICLES_PER_BLOCK = 2000
DIR_BLOQUES = "temp/cdroot/cdpedia/bloques"

# Directorio de archivos temporales
DIR_TEMP = "temp"

# Donde irán los archivos del índice
DIR_INDICE = "temp/indice"

# Directorio destino de los archivos preprocesados.
DIR_PREPROCESADO = DIR_TEMP + "/preprocesado"

# Directorio de los archivos ya listos para inclusión
DIR_PAGSLISTAS = DIR_TEMP + "/paglistas"

# Directorio de las imágenes ya listas para inclusión
DIR_IMGSLISTAS = DIR_TEMP + "/imglistas"

# Cantidad de imágenes por bloque
IMAGES_PER_BLOCK = 10

# Directorio raiz de los archivos que van al CD
DIR_CDBASE = "temp/cdroot"

# Directorio de los archivos estáticos: imagenes, hojas de estilo, etc
DIR_ASSETS = "temp/cdroot/cdpedia/assets"

# Directorio de los archivos estáticos de origen
DIR_SOURCE_ASSETS = "resources/static"

# Decidimos cuales páginas quedaron
PAG_ELEGIDAS = "temp/pag_elegidas.txt"

# Logs varios:
LOG_REDIRECTS = DIR_TEMP + "/redirects.txt"
LOG_PREPROCESADO = DIR_TEMP + "/preprocesado.txt"
LOG_IMAGENES = DIR_TEMP + "/imagenes.txt"
LOG_IMAGPROC = DIR_TEMP + "/imag_proc.txt"
LOG_REDUCCION = DIR_TEMP + "/reduccion.txt"
LOG_REDUCDONE = DIR_TEMP + "/reduc_done.txt"

# Formato general de los logs:
SEPARADOR_COLUMNAS = '|'

# Directorios especiales con metadata y cosas que no son los HTMLs de las
# páginas en sí
ASSETS = ["skins", "misc"]

# Nombre de la edicion especial, modifica el INDEX y ASSETS en código
EDICION_ESPECIAL = None
#EDICION_ESPECIAL = "educar"

# Primera página que se abrirá en el browser.
# Para ir a la portada de cdpedia dejar ""
INDEX = "index.html"

# PATH del archivo que contiene los artículos destacados de donde se
# seleccionará el que se muestra en la página principal
# Si no hay destacados debe ser None
DESTACADOS = 'destacados.txt'

# Tiempo de espera máxima para actualización del browser_watchdog
BROWSER_WD_SECONDS = 60

# Comando externo para convertir en HTML en texto, para extraer las palabras
# del documento. Lynx es el default, pero requiere que esté instalado en el host.
# W3m está disponible en todos los Ubuntus. %s se expande al path al archivo
CMD_HTML_A_TEXTO = 'w3m -dump -T "text/html" -I utf-8 -O utf-8 -s -F -no-graph %s'
# CMD_HTML_A_TEXTO = 'lynx -nolist -dump -display_charset=UTF-8 %s'

# Límites de cantidades de páginas a incluir
####  Para el DVD:
#LIMITE_PAGINAS = 500000
##  Para el CD:
LIMITE_PAGINAS = 85500
##  Devel
#LIMITE_PAGINAS = 180

# Pares cantidad/escala. (n, m) se lee como "el top n% de LIMITE_PAGINAS
# tendrán las imágenes al m%.  Hay que incluir los extremos 100 y 0 de escala
# (ordenados),  y los porcentajes de cantidad tienen que sumar 100
####  Para el DVD: (size max: DVD+R, 12cm:  4,700,372,992 bytes)
#ESCALA_IMAGS = [
#    (18, 100),  # 16       18       20
#    (23,  75),  # 17       20       25
#    (59,  50),  # 32       37       45
#    ( 0,   0),  #  = 4.1    = 4.3    = 4.5
#]
##  Para el CD: (size max: 12cm, 80min:  737,280,000 bytes)
ESCALA_IMAGS = [
    ( 2, 100),
    ( 4,  75),
    ( 4,  50),
    (90,   0),
]

# "Namespaces" que tenemos, y un flag que indica si son  válidos o no (la
# mayoría de las páginas no tienen namespace, esas entran todas)
# Lo que está ahora es sumamente arbitrario, no tengo idea de qué es lo mejor
# Referencia rápida: http://es.wikipedia.org/wiki/Especial:Prefixindex

NAMESPACES = {
    u"Anexo": True,
    u"Anexo_Discusión": False,
    u"Ayuda": True,
    u"Categoría": True,
    u"Categoría_Discusión": False,
    u"Discusión": False,
    u"Imagen": False,
    u"Plantilla": False,
    u"Plantilla_Discusión": False,
    u"Portal": True,
    u"Portal_Discusión": False,
    u"Usuario": False,
    u"Usuario_Discusión": False,
    u"Wikipedia": False,
    u"Wikipedia_Discusión": False,
    u"Wikiproyecto": False,
    u"Wikiproyecto_Discusión": False,
    u"Archivo": False,
    u"Especial": False,
}

INCLUDE = [
    u"Wikipedia:Acerca_de",
    u"Wikipedia:Limitación_general_de_responsabilidad",
    u"Wikipedia:Aviso_de_riesgo",
    u"Wikipedia:Aviso_médico",
    u"Wikipedia:Aviso_legal",
    u"Wikipedia:Aviso_de_contenido",
    u"Wikipedia:Derechos_de_autor",
]

# Dump de Junio 2008
#Mostrando los resultados para un total de 1362473 archivos que ocupan 18353.39 MB:
#
#  Raiz                                                            Cant      Cant%  Tamaño   Tamaño%
#  None                                                           629532     46.21%  7009 MB    38.19%
#  Imagen                                                         248624     18.25%  4907 MB    26.74%
#  Usuario_Discusión                                              234779     17.23%  3065 MB    16.70%
#  Usuario                                                         53582      3.93%  955 MB     5.21%
#  Discusión                                                       80748      5.93%  711 MB     3.88%
#  Categoría                                                       65065      4.78%  685 MB     3.74%
#  Wikipedia                                                       10773      0.79%  387 MB     2.11%
#  Anexo                                                            9913      0.73%  285 MB     1.56%
#  Plantilla                                                       11738      0.86%   92 MB     0.50%
#  Wikiproyecto                                                     2311      0.17%   68 MB     0.37%
#  Portal                                                           5200      0.38%   57 MB     0.31%
#  Wikipedia_Discusión                                              1229      0.09%   28 MB     0.16%
#  Wikiproyecto_Discusión                                            629      0.05%   22 MB     0.12%
#  Plantilla_Discusión                                              1615      0.12%   15 MB     0.08%
#  Categoría_Discusión                                              1502      0.11%   11 MB     0.06%
#  Anexo_Discusión                                                  1498      0.11%   10 MB     0.06%
#  Ayuda                                                             169      0.01%    3 MB     0.02%
#  Portal_Discusión                                                  273      0.02%    2 MB     0.02%

# Dump de Septiembre 2007
# Mostrando los resultados para un total de 758669 archivos que ocupan 8757.33 MB:
#
#   Raiz                                                   Cant      Cant%  Tamaño      Tam.%
#   None                                                  459793     60.61%  4730 MB   54.02%
#   Usuario_Discusión                                     125147     16.50%  1736 MB   19.83%
#   Usuario                                                35891      4.73%  701 MB     8.01%
#   Discusión                                              58106      7.66%  487 MB     5.56%
#   Categoría                                              46642      6.15%  481 MB     5.50%
#   Wikipedia                                               8013      1.06%  264 MB     3.03%
#   Anexo                                                   4495      0.59%  128 MB     1.47%
#   Plantilla                                               9101      1.20%   65 MB     0.75%
#   Wikiproyecto                                            1517      0.20%   45 MB     0.52%
#   Portal                                                  3127      0.41%   33 MB     0.39%
#   Wikipedia_Discusión                                      876      0.12%   17 MB     0.20%
#   Wikiproyecto_Discusión                                   436      0.06%   13 MB     0.15%
#   Plantilla_Discusión                                     1353      0.18%   12 MB     0.14%
#   Categoría_Discusión                                     1008      0.13%    8 MB     0.09%
#   Anexo_Discusión                                          605      0.08%    4 MB     0.05%
#   Ayuda                                                    154      0.02%    2 MB     0.03%
#   Portal_Discusión                                         209      0.03%    2 MB     0.02%
#
#
# Dump de Noviembre 2006
# Mostrando los resultados para un total de 171007 archivos que ocupan 1559.29 MB:
#
#   Raiz                                             Cant Cant%  Tamaño Tamaño%
#   Imagen                                          24832  15 %  200 MB  13 %
#   Usuario_Discusión                                9107   5 %  107 MB   7 %
#   Categoría                                        8946   5 %   75 MB   5 %
#   Discusión                                       10591   6 %   69 MB   4 %
#   Wikipedia                                        1775   1 %   67 MB   4 %
#   Usuario                                          5209   3 %   52 MB   3 %
#   Plantilla                                        3107   2 %   18 MB   1 %
#   MediaWiki                                        1542   1 %    7 MB   0 %
#   Imagen_Discusión                                  252   0 %    4 MB   0 %
#   Wikipedia_Discusión                               307   0 %    3 MB   0 %
#   Portal                                            355   0 %    3 MB   0 %
#   Categoría_Discusión                               300   0 %    2 MB   0 %
#   Wikiproyecto                                       97   0 %    1 MB   0 %
#   Plantilla_Discusión                               170   0 %    1 MB   0 %
#   Wikiproyecto_Discusión                             49   0 %    1 MB   0 %
