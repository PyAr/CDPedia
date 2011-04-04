# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py para consulta, se utiliza directamente
para crear el índice.
"""

import os
import codecs
import unicodedata
import config
import subprocess
import re
import threading
import shutil

#from .easy_index import Index
from .compressed_index import Index

usage = """Indice de títulos de la CDPedia

Para generar el archivo de indice hacer:

  cdpindex.py fuente destino [max] [dirbase]

    fuente: archivo con los títulos
    destino: en donde se guardará el índice
    max: cantidad máxima de títulos a indizar
    dirbase: de dónde dependen los archivos
"""

# Buscamos todo hasta el último guión no inclusive, porque los
# títulos son como "Zaraza - Wikipedia, la enciclopedia libre"
SACATIT = re.compile(".*?<title>([^<]*)\s+-", re.S)

# separamos por palabras
PALABRAS = re.compile("\w+", re.UNICODE)

# cantidad de palabras a incluir en el resumen de cada artículo
CANT_CARS_RESUMEN = 230

def normaliza(txt):
    """Recibe una frase y devuelve sus palabras ya normalizadas."""
    txt = unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').lower()
    return txt

def _getHTMLTitle(arch):
    # Todavia no soportamos redirect, asi que todos los archivos son
    # válidos y debería tener TITLE en ellos
    html = codecs.open(arch, "r", "utf8").read()
    m = SACATIT.match(html)
    if m:
        tit = m.groups()[0]
    else:
        tit = u"<sin título>"
    return tit

def _getPalabrasHTML(arch):
    # FIXME: esta función es para cuando hagamos fulltext
    arch = os.path.abspath(arch)
    cmd = config.CMD_HTML_A_TEXTO % arch
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    txt = p.stdout.read()
    txt = txt.decode("utf8")
    return txt

def _get_primeras_palabras(arch):
    html = codecs.open(arch, "r", "utf8").read()

    # nos paramos luego del primer párrafo
    delimiter = "<p>"
    try:
        pos = html.index(delimiter) + len(delimiter)
    except ValueError:
        pos = 0
    html = html[pos:]

    # hasta que termine el párrafo
    delimiter = "</p>"
    try:
        pos = html.index(delimiter)
    except ValueError:
        pos = 0
    html = html[:pos]

    # borramos todo lo que son tags
    html = re.sub("<.*?>", "", html)

    # borramos todo los tabs y enters
    html = re.sub("[\\t\\n]", "", html)

    # mostramos las indicadas, si hay
    if html:
        html = html[:CANT_CARS_RESUMEN] + "..."
    return html


class IndexInterface(threading.Thread):
    """Procesa toda la info para interfacear con el índice.

    Lo que guardamos en el índice para cada palabra es:

     - nomhtml: el path al archivo
     - titulo: del artículo
     - puntaje: para relativizar la importancia del artículo
    """
    def __init__(self, directory):
        super(IndexInterface, self).__init__()
        self.ready = threading.Event()
        self.directory = directory

    def is_ready(self):
        return self.ready.isSet()

    def run(self):
        """Levanta el índice."""
        self.indice = Index(self.directory)
        self.ready.set()

    def listado_palabras(self):
        """Devuelve las palabras."""
        self.ready.wait()
        return sorted(self.indice.keys())

    def listado_valores(self):
        """Devuelve la info de todos los artículos."""
        self.ready.wait()
        return sorted(set(x[:2] for x in self.indice.values()))

    def get_random(self):
        """Devuelve un artículo al azar."""
        self.ready.wait()
        value = self.indice.random()
        return value[:2]

    def search(self, words):
        """Busca palabras completas en el índice."""
        self.ready.wait()
        pals = PALABRAS.findall(normaliza(words))
        return self.indice.search(pals)

    def partial_search(self, words):
        """Busca palabras parciales en el índice."""
        self.ready.wait()
        pals = PALABRAS.findall(normaliza(words))
        return self.indice.partial_search(pals)


def filename2palabras(fname):
    """Transforma un filename en sus palabras y título."""
    if fname.endswith(".html"):
        fname = fname[:-5]
    x = normaliza(fname)
    p = x.split("_")
    t = " ".join(p)
    return p, t


def generar_de_html(dirbase, verbose):
    # lo importamos acá porque no es necesario en producción
    from src.preproceso import preprocesar

    # armamos las redirecciones
    redirs = {}
    for linea in codecs.open(config.LOG_REDIRECTS, "r", "utf-8"):
        orig, dest = linea.strip().split(config.SEPARADOR_COLUMNAS)

        # del original, que es el que redirecciona, no tenemos título, así
        # que sacamos las palabras del nombre de archivo mismo... no es lo
        # mejor, pero es lo que hay...
        palabras, titulo = filename2palabras(orig)
        redirs.setdefault(dest, []).append((palabras, titulo))

    filenames = preprocesar.get_top_htmls()

    def gen():
        for dir3, arch, puntaje in filenames:
            # info auxiliar
            nomhtml = os.path.join(dir3, arch)
            nomreal = os.path.join(dirbase, nomhtml)
            if os.access(nomreal, os.F_OK):
                titulo = _getHTMLTitle(nomreal)
                primtexto = _get_primeras_palabras(nomreal)
            else:
                print "WARNING: Archivo no encontrado:", nomreal
                continue

            if verbose:
                print "Agregando al índice [%r]  (%r)" % (titulo, nomhtml)

            # a las palabras del título le damos mucha importancia: 50, más
            # el puntaje original sobre 1000, como desempatador
            ptje = 50 + puntaje//1000
            for pal in PALABRAS.findall(normaliza(titulo)):
                yield pal, (nomhtml, titulo, ptje, True, primtexto)

            # pasamos las palabras de los redirects también que apunten
            # a este html, con el mismo puntaje
            if arch in redirs:
                for (palabras, titulo) in redirs[arch]:
                    for pal in palabras:
                        yield pal, (nomhtml, titulo, ptje, False, "")

            # FIXME: las siguientes lineas son en caso de que la generación
            # fuese fulltext, pero no lo es (habrá fulltext en algún momento,
            # pero será desde los bloques, no desde el html, pero guardamos
            # esto para luego)
            #
            # # las palabras del texto importan tanto como las veces que están
            # all_words = {}
            # for pal in PALABRAS.findall(normaliza(palabs_texto)):
            #     all_words[pal] = all_words.get(pal, 0) + 1
            # for pal, cant in all_words.items():
            #     yield pal, (nomhtml, titulo, cant)

    # nos aseguramos que el directorio esté virgen
    if os.path.exists(config.DIR_INDICE):
        shutil.rmtree(config.DIR_INDICE)
    os.mkdir(config.DIR_INDICE)

    Index.create(config.DIR_INDICE, gen())
    return len(filenames)
