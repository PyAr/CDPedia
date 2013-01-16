# -*- coding: utf-8 -*-

# Versión de la CDPedia
VERSION = '0.7.1'

# This should be set to the hostname or address of the server.
# Eg: "localhost", "192.168.1.1", "cdpedia.myserver.org"
HOSTNAME = "localhost"

# The port address to bind the server. If not daemon mode, the port used
# will be the first free port starting from PORT
PORT = 8000

# User Server mode True when cdpedia will be used in a centralized server
# configuration. If SERVER_MODE is False it must be used onli in localhost.
SERVER_MODE = False

# Nombre de la edicion especial, modifica el INDEX y ASSETS en código
EDICION_ESPECIAL = None
#EDICION_ESPECIAL = "educar"

# Ubicación de los archivos estáticos online
# Debe tener la barra al final
URL_WIKIPEDIA = u"http://es.wikipedia.org/"
IDIOMA = "es"

# Directorios especiales con metadata y cosas que no son los HTMLs de las
# páginas en sí
ASSETS = ["static"]

COMPRESSED_ASSETS = ['tutorial.tar.bz2']

ALL_ASSETS = ASSETS + COMPRESSED_ASSETS + ["images",  "extern"]
if EDICION_ESPECIAL is not None:
    ALL_ASSETS.append(EDICION_ESPECIAL)

# Primera página que se abrirá en el browser.
# Para ir a la portada de cdpedia dejar ""
INDEX = "index.html"

# PATH del archivo que contiene los artículos destacados de donde se
# seleccionará el que se muestra en la página principal
# Si no hay destacados debe ser None
DESTACADOS = 'destacados.txt'

# Para revisar la página inicial de CDPedia con cada artículo destacado se
# debe poner esta variable en True y cada vez que se cargué la página inicial
# se irán mostrando en orden los destacados.
DEBUG_DESTACADOS = False

# Tiempo de espera máxima, en segundos, para actualización del browser_watchdog.
# Usar BROWSER_WD_SECONDS = 0 para desactivar el watchdog.
BROWSER_WD_SECONDS = 120

# Quantity of default search results per page
SEARCH_RESULTS = 20

# info para el compresor / decompresor
ARTICLES_PER_BLOCK = 2000
DIR_BLOQUES = "temp/bloques"

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
IMAGES_PER_BLOCK = 200

# Directorio raiz de los archivos que van al CD
DIR_CDBASE = "temp/cdroot"

# Directorio de los archivos estáticos: imagenes, hojas de estilo, etc
DIR_ASSETS = "temp/cdroot/cdpedia/assets"

# Directorio de los archivos estáticos de origen
DIR_SOURCE_ASSETS = "resources"

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

# Comando externo para convertir en HTML en texto, para extraer las palabras
# del documento. Lynx es el default, pero requiere que esté instalado en el host.
# W3m está disponible en todos los Ubuntus. %s se expande al path al archivo
CMD_HTML_A_TEXTO = 'w3m -dump -T "text/html" -I utf-8 -O utf-8 -s -F -no-graph %s'
# CMD_HTML_A_TEXTO = 'lynx -nolist -dump -display_charset=UTF-8 %s'

# Límites de cantidades de páginas a incluir
LIMITE_PAGINAS = {
    'tar-big': 5000000,   # very big number, we want them all!
    'dvd9': 5000000,   # very big number, we want them all!
    'dvd5': 5000000,   # very big number, we want them all!
    'tar-med': 400000,
    'cd': 78500,
    'xo': 5000,
    'beta': 20000,   # sample version to distribute for others to QA
}

# Pares cantidad/escala. (n, m) se lee como "el top n% de LIMITE_PAGINAS
# tendrán las imágenes al m%.  Hay que incluir los extremos 100 y 0 de escala
# (ordenados),  y los porcentajes de cantidad tienen que sumar 100
ESCALA_IMAGS = {
    'tar-big': [   # we aim for 8 to 10 GB
        (10, 100),
        (25,  75),
        (65,  50),
        (00,   0),
    ],
    'tar-med': [   # we aim for 2 to 3 GB
        ( 4, 100),
        ( 8,  75),
        ( 8,  50),
        (80,   0),
    ],
    'dvd9': [  # size max: DVD-R DL, 12cm:  8,543,666,176 bytes
        (10, 100),  # 20           15           10
        (25,  75),  # 30           25           20
        (65,  50),  # 50           60           70
        (00,   0),  # 9190309888   8861982720   8525170688
    ],
    'dvd5': [  # size: DVD-R SL, 12cm:  4,700,319,808 bytes
        ( 4, 100),
        ( 4,  75),
        (16,  50),
        (76,   0),
    ],
    'xo': [
        ( 0, 100),
        ( 0,  75),
        ( 5,  50),
        (95,   0),
    ],
    'cd': [  # size max: 12cm, 80min:  737,280,000 bytes
        ( 1, 100),
        ( 2,  75),
        ( 3,  50),
        (94,   0),
    ],
    'beta': [
        ( 2, 100),
        ( 4,  75),
        ( 4,  50),
        (90,   0),
    ],
}

# validamos los porcentajes de lo que acabamos de escribir arriba
for _vers, escalas in ESCALA_IMAGS.items():
    _porc_escala = [x[1] for x in escalas]
    if max(_porc_escala) != 100 or min(_porc_escala) != 0:
        raise ValueError(u"Error en los extremos de ESCALA_IMAGS (%s)" % _vers)
    if sorted(_porc_escala, reverse=True) != _porc_escala:
        raise ValueError(u"Los % de escala no están ordenados (%s)" % _vers)
    if sum(x[0] for x in escalas) != 100:
        raise ValueError(u"Los % de ESCALA_IMAGS no suman 100 (%s)" % _vers)
_vers_imags = set(ESCALA_IMAGS)
_vers_pags = set(LIMITE_PAGINAS)
if _vers_pags != _vers_imags:
    raise ValueError("Different versions between "
                     "ESCALA_IMAGS and LIMITE_PAGINAS")
VALID_VERSIONS = _vers_imags


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
