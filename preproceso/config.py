#!/usr/bin/python
# -*- coding: utf-8 -*-

import preprocesadores as pr
from re import compile, MULTILINE, DOTALL

idioma = "es"

dir_raiz = "es"
dir_origen = "es/u"
dir_procesado = "procesado"

salida_redirects = "redirects.txt"
salida_omitido = "omitido.txt"
salida_preproceso = "procesado.txt"

preprocesadores = [
    pr.omitir_namespaces,
    pr.omitir_redirects,
    pr.extraer_contenido,
    pr.peishranc,
    pr.tamanio
]
namespaces_a_omitir = [
    "Usuario",
    "Imagen",
    "Discusión",
    #"MediaWiki", # -- por ahora no va, porque entre estos items se encuentran los .css, algunas imagenes y .js
    "Plantilla",
]

# deberia dar algo como "(?:Usuario.*|Imagen[^~]*|Discusi.*|MediaWiki.*|Plantilla.*)~"
buscar_namespaces_omisibles = compile(r'(?:%s)[^~]*~' % '|'.join(namespaces_a_omitir)).match
buscar_redirects = compile(r'<meta http-equiv="Refresh" content="\d;url=([^"]+)" />').search
buscar_contenido = compile(r'(<h1 class="firstHeading">.+</h1>).*<!-- start content -->\s*(.+)\s*<!-- end content -->', MULTILINE|DOTALL).search
buscar_enlaces = compile(r'<a\s+[^>]*?href="(\.\.\/[^"]+\.html)"').findall

urlwikipedia = "http://download.wikimedia.org/static/"

# Dump de Septiembre 2007
# Mostrando los resultados para un total de 758669 archivos que ocupan 8757.33 MB:
# 
#   Raiz                                                   Cant      Cant%  Tamaño   Tamaño%
#   None                                                  459793     60.61%  4730 MB    54.02%
#   Usuario_Discusión                                     125147     16.50%  1736 MB    19.83%
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
#
# MediaWiki - Por lo que se ve son mensajes de administracion interna de MediaWiki (errores
#   de que falta un comando, de que se marco como revisado un articulo, etc).
# Discusi.* : Discusion del articulo y usuarios
# Imagen : Historial de las imagenes, tipo de copyright, etc
# Usuario : Contiene informacion de los usuarios, lo que les interesa, etc
# Plantilla : Plantillas :), de ejemplo para hacer los articulos.


# Ojo que tiene que tener la barra al final
