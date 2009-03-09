# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py para consulta, se utiliza directamente
para crear el índice.
"""

import shelve
import time
import sys
import os
import codecs
import random
import unicodedata
import operator
import glob
import config
import HTMLParser
import re

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

def normaliza(txt):
    '''Recibe una frase y devuelve sus palabras ya normalizadas.'''
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


class _MyHTMLParser(HTMLParser.HTMLParser):

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.all_words = []
        self.inbody = False

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.inbody = True

    def handle_endtag(self, tag):
        if tag == 'body':
            self.inbody = False

    def handle_data(self, data):
        if self.inbody:
            self.all_words.append(data)

def _getPalabrasHTML(arch):
    html = codecs.open(arch, "r", "utf8").read()
    mhp = _MyHTMLParser()
    mhp.feed(html)
    return " ".join(mhp.all_words)

class Index(object):
    '''Maneja todo el índice.

    La idea es ofrecer funcionalidad, después vemos tamaño y tiempos.
    '''

    def __init__(self, filename=None, verbose=False):
        self.verbose = verbose
        if filename is not None:
            self.open(filename)

    def listar(self):
        '''Muestra en stdout las palabras y los artículos referenciados.'''
        id_shelf = self.id_shelf
        for palabra, docid_ptje in sorted(self.word_shelf.items()):
            docids = [x[0] for x in docid_ptje] # le sacamos la cant
            print "%s: %s" % (palabra, [id_shelf[str(x)][1] for x in docids])

    def listado_completo(self):
        '''Devuelve la info de todos los artículos.'''
        return sorted(self.id_shelf.values())

    def get_random(self):
        '''Devuelve un artículo al azar.'''
        return random.choice(self.id_shelf.values())

    def _merge_results(self, results):
        # vemos si tenemos algo más que vacio
        results = filter(bool, results)
        if not results:
            return []

        # el resultado final es la intersección de los parciales ("and")
        intersectados = reduce(operator.iand, (set(d) for d in results))
        final = {}
        for result in results:
            for pagtit, ptje in result.items():
                if pagtit in intersectados:
                    final[pagtit] = final.get(pagtit, 0) + ptje

        final = [(pag, tit, ptje) for (pag, tit), ptje in final.items()]
        return sorted(final, key=operator.itemgetter(2), reverse=True)


    def search(self, words):
        '''Busca palabras completas en el índice.'''
        results = []
        for word in PALABRAS.findall(normaliza(words)):
            if word not in self.word_shelf:
                continue

            result = {}
            for docid, ptje in self.word_shelf[word]:
                pag = self.id_shelf[str(docid)]
                result[pag] = result.get(pag, 0) + ptje
            results.append(result)

        return self._merge_results(results)

    def detailed_search(self, words):
        '''Busca palabras parciales en el índice.'''
        results = []
        for word in PALABRAS.findall(normaliza(words)):
            # tomamos cuales palabras reales tienen adentro las palabra parcial
            resultword = []
            for guardada in self.word_shelf:
                if word in guardada:
                    resultword.append(guardada)
            if not resultword:
                continue

            # efectivamente, tenemos algunas palabras reales
            result = {}
            for realword in resultword:
                for docid, ptje in self.word_shelf[realword]:
                    pagtit = self.id_shelf[str(docid)]
                    result[pagtit] = result.get(pagtit, 0) + ptje
            results.append(result)

        return self._merge_results(results)

    def create(self, salida, fuente):
        '''Crea los índices.'''
        # borramos lo viejo y arrancamos
        viejos = glob.glob("%s*" % salida)
        for arch in viejos:
            os.remove(arch)
        self.open(salida)

        # fill them
        for docid, (nomhtml, titulo, palabras_texto) in enumerate(fuente):
            if self.verbose:
                print "Agregando al índice [%r]  (%r)" % (titulo, nomhtml)
            # docid -> info final
            self.id_shelf[str(docid)] = (nomhtml, titulo)

            # palabras -> docid
            # a las palabras del título le damos mucha importancia: 50
            for pal in PALABRAS.findall(normaliza(titulo)):
                # parece no andar el setdefault del shelve
#                self.word_shelf.setdefault(pal, set()).add(docid)
                if pal in self.word_shelf:
                    info = self.word_shelf[pal]
                    info.append((docid, 50))
                    self.word_shelf[pal] = info
                else:
                    self.word_shelf[pal] = [(docid, 50)]

            # las palabras del texto importan tanto como las veces que están
            all_words = {}
            for pal in PALABRAS.findall(normaliza(palabras_texto)):
                all_words[pal] = all_words.get(pal, 0) + 1

            for pal, cant in all_words.items():
                if pal in self.word_shelf:
                    info = self.word_shelf[pal]
                    info.append((docid, cant))
                    self.word_shelf[pal] = info
                else:
                    self.word_shelf[pal] = [(docid, cant)]

        # close everything
        self.id_shelf.close()
        self.word_shelf.close()
        return docid

    def open(self, filename):
        '''Abre los archivos.'''
        wordsfilename = filename + ".words"
        idsfilename = filename + ".ids"
        if self.verbose:
            print "Opening", wordsfilename
        self.word_shelf = shelve.open(wordsfilename)
        if self.verbose:
            print "Opening", idsfilename
        self.id_shelf = shelve.open(idsfilename)

def generar(src_info, verbose, full_text=False):
    return _create_index(config.LOG_PREPROCESADO, config.PREFIJO_INDICE,
                        dirbase=src_info, verbose=verbose, full_text=full_text)

def _create_index(fuente, salida, dirbase="", verbose=False, full_text=False):
    # lo importamos acá porque no es necesario en producción
    from src import utiles

    index = Index(verbose=verbose)

    def fix(letra):
        if letra == " ":
            letra = "_"
        return letra

    def get3letras(arch):
        arch = arch[:-5] # le sacamos el .html
        arch = arch.lower()
        arch = (arch+"   ")[:3] # queremos las primeras 3 llenando con espacios
        return map(fix, arch)

    def gen():
        fh = codecs.open(fuente, "r", "utf8")
        fh.next() # título
        for i,linea in enumerate(fh):
            arch = linea.split()[0].strip()
            if not arch.endswith(".html"):
                continue

            (categoria, restonom) = utiles.separaNombre(arch)
            if verbose:
                print "Indizando [%d] %s" % (i, arch.encode("utf8"))
            # info auxiliar
            a,b,c = get3letras(restonom)
            nomhtml = os.path.join(a, b, c, arch)
            nomreal = os.path.join(dirbase, nomhtml)
            if os.access(nomreal, os.F_OK):
                titulo = _getHTMLTitle(nomreal)
                if full_text:
                    palabras = _getPalabrasHTML(nomreal)
                else:
                    palabras = []
            else:
                titulo = ""
                print "WARNING: Archivo no encontrado:", nomreal

            # si tenemos max, lo respetamos y entregamos la info
            if max is not None and i > max:
                raise StopIteration
            yield (nomhtml, titulo, palabras)

    cant = index.create(salida, gen())
    return cant

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print usage
        sys.exit()

    tini = time.time()
    cant = _create_index(*sys.argv[1:])
    delta = time.time()-tini
    print "Indice creado! (%.2fs)" % delta
    print "Archs: %d  (%.2f mseg/arch)" % (cant, 1000*delta/cant)
