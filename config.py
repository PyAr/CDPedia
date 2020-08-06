# -*- coding: utf-8 -*-

# Copyright 2008-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/

import os

import yaml

# Versión de la CDPedia
VERSION = '0.8.4'

# This should be set to the hostname or address of the server.
# Eg: "localhost", "192.168.1.1", "cdpedia.myserver.org"
HOSTNAME = "127.0.0.1"

# The port address to bind the server. If not daemon mode, the port used
# will be the first free port starting from PORT
PORT = 8000

# User Server mode True when cdpedia will be used in a centralized server
# configuration. If SERVER_MODE is False it must be used only in localhost.
SERVER_MODE = False

# Nombre de la edicion especial, modifica el INDEX y ASSETS en código
EDICION_ESPECIAL = None
# EDICION_ESPECIAL = "educar"

# Language of CDPedia.
# Value will be set dynamically at init time (don't set it here).
LANGUAGE = None

# Location of online static files, depends on LANGUAGE.
# Value will be set dynamically at init time (don't set it here).
URL_WIKIPEDIA = None

# Template for setting URL_WIKPEDIA param, must contain the final slash.
URL_WIKIPEDIA_TPL = "http://{lang}.wikipedia.org/"

# Localization of CDPedia interface
# Value will be set dynamically at init time (don't set it here).
LOCALE = None

# Directorios especiales con metadata y cosas que no son los HTMLs de las
# páginas en sí
ASSETS = ["static"]
COMPRESSED_ASSETS = ['tutorial.tar.xz']
ALL_ASSETS = ASSETS + COMPRESSED_ASSETS + ["images", "extern"]
if EDICION_ESPECIAL is not None:
    ALL_ASSETS.append(EDICION_ESPECIAL)

# Primera página que se abrirá en el browser.
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

# Generation language will be saved in this file
LANGUAGE_FILE = os.path.join(DIR_BLOQUES, 'language.txt')

# Logs varios:
LOG_REDIRECTS = DIR_TEMP + "/redirects.txt"
LOG_PREPROCESADO = DIR_TEMP + "/preprocesado.txt"
LOG_IMAGENES = DIR_TEMP + "/imagenes.txt"
LOG_IMAGPROC = DIR_TEMP + "/imag_proc.txt"
LOG_REDUCCION = DIR_TEMP + "/reduccion.txt"
LOG_REDUCDONE = DIR_TEMP + "/reduc_done.txt"
LOG_TITLES = DIR_TEMP + "/titles.txt"
LOG_LOCALE = DIR_TEMP + "/locale.txt"

# prefix for URL of local images
IMAGES_URL_PREFIX = "/images/"

# enable mandatory inclusion of some images in final distribution (e.g. SVG)
IMAGES_REQUIRED = True
LOG_IMAGES_REQUIRED = DIR_TEMP + '/images_required.txt'

# enable embedding of some images in HTML source (e.g. small SVG)
EMBED_IMAGES = True
LOG_IMAGES_EMBEDDED = DIR_TEMP + '/images_embed.txt'

# Validate translation before generating a CDPedia in the specified language.
# Interrupt process if validation fails. In test mode, show validation result
# but don't interrupt process.
VALIDATE_TRANSLATION = True

# Formato general de los logs:
SEPARADOR_COLUMNAS = '|'

# Tag de que la info viene de un recurso dinámico de mucha importancia
DYNAMIC = '__dynamic__'

# Comando externo para convertir en HTML en texto, para extraer las palabras
# del documento. Lynx es el default, pero requiere que esté instalado en el host.
# W3m está disponible en todos los Ubuntus. %s se expande al path al archivo
CMD_HTML_A_TEXTO = 'w3m -dump -T "text/html" -I utf-8 -O utf-8 -s -F -no-graph %s'

# load configuration for languages and validate
_path = os.path.join(os.path.dirname(__file__), "imagtypes.yaml")
with open(_path, "rt") as fh:
    imagtypes = yaml.safe_load(fh)
for lang, imtypes in imagtypes.items():
    for imtype, imdata in imtypes.items():
        if sum(imdata['image_reduction']) != 100:
            raise ValueError("Image reduction config doesn't add 100%% for "
                             "lang=%r imagetype=%r" % (lang, imtype))

# this variable will be overwritten at init time according to what
# is being generated
imageconf = None
