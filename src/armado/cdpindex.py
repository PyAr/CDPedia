# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py para consulta, se utiliza directamente
para crear el índice.
"""

from __future__ import with_statement

import cPickle
import time
import sys
import os
import codecs
import random
import unicodedata
import operator
import glob
import config
import subprocess
import re
from bz2 import BZ2File as CompressedFile

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

def _getPalabrasHTML(arch):
    arch = os.path.abspath(arch)
    cmd = config.CMD_HTML_A_TEXTO % arch
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    txt = p.stdout.read()
    txt = txt.decode("utf8")
    return txt

class Index(object):
    '''Maneja todo el índice.

    La idea es ofrecer funcionalidad, después vemos tamaño y tiempos.
    '''

    def __init__(self, filename, verbose=False):
        self.filename = filename
        self._cache_indx = {}

        # sólo abrimos "words", ya que "ids" es por pedido
        wordsfilename = filename + ".words.bz2"

        if verbose:
            print "Abriendo", wordsfilename
        fh = CompressedFile(wordsfilename, "rb")
        self.word_shelf = cPickle.load(fh)
        fh.close()

    def _get_info_id(self, *keys):
        '''Devuelve la coincidencia para la clave.'''
        # separamos los keys en función del archivo
        cuales = {}
        for k in keys:
            cual = hash(k) % 10
            cuales.setdefault(cual, []).append(k)

        # juntamos la info de cada archivo
        resultados = {}
        for cual, keys in cuales.items():
            if cual not in self._cache_indx:
                idsfilename = "%s-%d.ids.bz2" % (self.filename, cual)
                fh = CompressedFile(idsfilename, "rb")
                idx = cPickle.load(fh)
                fh.close()
                self._cache_indx[cual] = idx
            else:
                idx = self._cache_indx[cual]
            resultados.update((k, idx[k]) for k in keys)

        return resultados

    def listar(self):
        '''Muestra en stdout las palabras y los artículos referenciados.'''
        for palabra, docid_ptje in sorted(self.word_shelf.items()):
            docids = [x[0] for x in docid_ptje] # le sacamos la cant
            data = [str(x)[1] for x in self._get_info_id(*docids).values()]
            print "%s: %s" % (palabra, data)

    def listado_valores(self):
        '''Devuelve la info de todos los artículos.'''
        vals = []
        for cual in range(10):
            idsfilename = "%s-%d.ids.bz2" % (self.filename, cual)
            fh = CompressedFile(idsfilename, "rb")
            ids = cPickle.load(fh)
            fh.close()
            vals.extend(ids.itervalues())
        return sorted(vals)

    def listado_palabras(self):
        '''Devuelve las palabras indexadas.'''
        return sorted(self.word_shelf.keys())

    def get_random(self):
        '''Devuelve un artículo al azar.'''
        cual = random.randint(0,9)
        idsfilename = "%s-%d.ids.bz2" % (self.filename, cual)
        fh = CompressedFile(idsfilename, "rb")
        ids = cPickle.load(fh)
        fh.close()
        return random.choice(ids.values())

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
            all_data = self.word_shelf[word]
            all_pags = self._get_info_id(*[x[0] for x in all_data])
            for docid, ptje in all_data:
                pag = all_pags[docid]
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
                all_data = self.word_shelf[realword]
                all_pags = self._get_info_id(*[x[0] for x in all_data])
                for docid, ptje in all_data:
                    pagtit = all_pags[docid]
                    result[pagtit] = result.get(pagtit, 0) + ptje
            results.append(result)

        return self._merge_results(results)

    @classmethod
    def create(cls, filename, fuente, verbose):
        '''Crea los índices.'''
        id_shelf = {}
        word_shelf = {}

        # fill them
        for docid, (nomhtml, titulo, palabs_texto, ptje) in enumerate(fuente):
            if verbose:
                print "Agregando al índice [%r]  (%r)" % (titulo, nomhtml)
            # docid -> info final
            id_shelf[docid] = (nomhtml, titulo)

            # palabras -> docid
            # a las palabras del título le damos mucha importancia: 50, más
            # el puntaje original sobre 1000, como desempatador
            for pal in PALABRAS.findall(normaliza(titulo)):
                word_shelf.setdefault(pal, []).append((docid, 50 + ptje//1000))

            # las palabras del texto importan tanto como las veces que están
            all_words = {}
            for pal in PALABRAS.findall(normaliza(palabs_texto)):
                all_words[pal] = all_words.get(pal, 0) + 1

            for pal, cant in all_words.items():
                word_shelf.setdefault(pal, []).append((docid, cant))

        # grabamos words
        wordsfilename = filename + ".words.bz2"
        if verbose:
            print "Grabando", wordsfilename
        fh = CompressedFile(wordsfilename, "wb")
        cPickle.dump(word_shelf, fh, 2)
        fh.close()

        if verbose:
            print "Grabando", idsfilename

        # separamos id_shelf en 10 diccionarios
        all_idshelves = [{} for i in range(10)]
        for k,v in id_shelf.iteritems():
            cual = hash(k) % 10
            all_idshelves[cual][k] = v

        # grabamos los 10 diccionarios donde corresponde
        for cual, shelf in enumerate(all_idshelves):
            idsfilename = "%s-%d.ids.bz2" % (filename, cual)
            fh = CompressedFile(idsfilename, "wb")
            cPickle.dump(shelf, fh, 2)
            fh.close()

        return docid+1

# Lo dejamos comentado para despues, para hacer el full_text desde los bloques
#
# def generar(src_info, verbose, full_text=False):
#     return _create_index(config.LOG_PREPROCESADO, config.PREFIJO_INDICE,
#                         dirbase=src_info, verbose=verbose, full_text=full_text)
#
#     def gen():
#         fh = codecs.open(fuente, "r", "utf8")
#         fh.next() # título
#         for i,linea in enumerate(fh):
#             partes = linea.split()
#             arch, dir3 = partes[:2]
#             if not arch.endswith(".html"):
#                 continue
#
#             (categoria, restonom) = utiles.separaNombre(arch)
#             if verbose:
#                 print "Indizando [%d] %s" % (i, arch.encode("utf8"))
#             # info auxiliar
#             nomhtml = os.path.join(dir3, arch)
#             nomreal = os.path.join(dirbase, nomhtml)
#             if os.access(nomreal, os.F_OK):
#                 titulo = _getHTMLTitle(nomreal)
#                 if full_text:
#                     palabras = _getPalabrasHTML(nomreal)
#                 else:
#                     palabras = []
#             else:
#                 titulo = ""
#                 print "WARNING: Archivo no encontrado:", nomreal
#
#             # si tenemos max, lo respetamos y entregamos la info
#             if max is not None and i > max:
#                 raise StopIteration
#             yield (nomhtml, titulo, palabras)
#
#     cant = Index.create(salida, gen(), verbose)
#     return cant

def generar_de_html(dirbase, verbose):
    # lo importamos acá porque no es necesario en producción
    from src import utiles
    from src.preproceso import preprocesar

    def gen():
        fileNames = preprocesar.get_top_htmls(config.LIMITE_PAGINAS)

        for i, (dir3, arch, puntaje) in enumerate(fileNames):
            if verbose:
                print "Indizando [%d] %s" % (i, arch.encode("utf8"))
            # info auxiliar
            nomhtml = os.path.join(dir3, arch)
            nomreal = os.path.join(dirbase, nomhtml)
            if os.access(nomreal, os.F_OK):
                titulo = _getHTMLTitle(nomreal)
                palabras = u""
            else:
                titulo = ""
                print "WARNING: Archivo no encontrado:", nomreal

            # si tenemos max, lo respetamos y entregamos la info
            if max is not None and i > max:
                raise StopIteration
            yield (nomhtml, titulo, palabras, puntaje)

    cant = Index.create(config.PREFIJO_INDICE, gen(), verbose)
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
