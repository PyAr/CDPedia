# -*- coding: utf-8 -*-

# Ubicación de los archivos estáticos online
# Debe tener la barra al final
URL_WIKIPEDIA = "http://download.wikimedia.org/static/"
IDIOMA = "es"

# info para el compresor / decompresor
ARTICLES_PER_BLOCK = 2000
DIR_BLOQUES = "temp/cdroot/bloques"

# Directorio de archivos temporales
DIR_TEMP = "temp"

# Los índices generados (a esto se le agrega las dos terminaciones)
PREFIJO_INDICE = "temp/wikiindex"

# Directorio destino de los archivos preprocesados.
DIR_PREPROCESADO = DIR_TEMP + "/preprocesado"

# Directorio de los archivos ya listos para inclusión
DIR_PAGSLISTAS = DIR_TEMP + "/paglistas"

# Directorio raiz de los archivos que van al CD
DIR_CDBASE = "temp/cdroot"

# Directorio de los archivos estáticos: imagenes, hojas de estilo, etc
DIR_ASSETS = "temp/cdroot/assets"

# Logs varios:
LOG_REDIRECTS = DIR_TEMP + "/redirects.txt"
LOG_PREPROCESADO = DIR_TEMP + "/preprocesado.txt"
LOG_IMAGENES = DIR_TEMP + "/imagenes.txt"

# Formato general de los logs:
SEPARADOR_COLUMNAS = '|'

# Directorios especiales con metadata y cosas que no son los HTMLs de las
# páginas en sí
ASSETS = ["skins", "misc", "raw"]

# Límites de cantidades de páginas a incluir, y de cuantas páginas con
# imágenes incluir
LIMITE_PAGINAS = 120000
LIMITE_IMAGENES = 13000

# "Namespaces" (espacios de nombres) que queremos excluir de la compilación.
# Por una cuestión de practicidad conviene comentar las lineas de los namespaces
# que sí queremos que entren.
# Lo que está ahora es sumamente arbitrario, no tengo idea de qué es lo mejor
# Referencia rápida: http://es.wikipedia.org/wiki/Especial:Prefixindex
NAMESPACES_INVALIDOS = [
    # 'Media',
    u'Especial',
    u'Discusión',
    u'Usuario',
    u'Usuario_Discusión',
    u'Wikipedia',
    u'Wikipedia_Discusión',
    u'Imagen',
    u'Imagen_Discusión',
    u'MediaWiki',
    u'MediaWiki_Discusión',
    u'Plantilla',
    u'Plantilla_Discusión',
    #'Ayuda',
    u'Ayuda_Discusión',
    #'Categoría',
    u'Categoría_Discusión',
    #'Portal',
    u'Portal_Discusión',
    #'Wikiproyecto',
    u'Wikiproyecto_Discusión',
    #'Anexo',
    u'Anexo_Discusión',
]

NAMESPACES = [
    u'Media',
    u'Especial',
    u'Discusión',
    u'Usuario',
    u'Usuario_Discusión',
    u'Wikipedia',
    u'Wikipedia_Discusión',
    u'Imagen',
    u'Imagen_Discusión',
    u'MediaWiki',
    u'MediaWiki_Discusión',
    u'Plantilla',
    u'Plantilla_Discusión',
    u'Ayuda',
    u'Ayuda_Discusión',
    u'Categoría',
    u'Categoría_Discusión',
    u'Portal',
    u'Portal_Discusión',
    u'Wikiproyecto',
    u'Wikiproyecto_Discusión',
    u'Anexo',
    u'Anexo_Discusión',
]

# Comando externo para convertir en HTML en texto, para extraer las palabras
# del documento. Lynx es el default, pero requiere que esté instalado en el host.
# W3m está disponible en todos los Ubuntus. %s se expande al path al archivo
#
CMD_HTML_A_TEXTO = 'w3m -dump -T "text/html" -I utf-8 -O utf-8 -s -F -no-graph %s'
# CMD_HTML_A_TEXTO = 'lynx -nolist -dump -display_charset=UTF-8 %s'


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
