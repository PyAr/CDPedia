# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py para consulta, se utiliza directamente
para crear el índice.
"""

import shelve, time, sys, os.path, re, codecs
import random
import unicodedata

import config

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

_cache = {}
def _norm_car(car):
    # devolvemos lo cacheado, si podemos
    try:
        return _cache[car]
    except KeyError:
        pass

    # si es una letra simple, no hace falta normalización, nos fijamos
    # primero porque es más rápido
    if ord(car) < 128:
        _cache[car] = car
        return car

    # descomponemos y vemos en qué caso estamos
    decomp = unicodedata.decomposition(car)
    if decomp == "":
        # no tiene
        res = car
    elif decomp.startswith("<compat>"):
        # compatibilidad
        utiles = [x for x in decomp.split()][1:]
        res = u"".join(unichr(int(x, 16)) for x in utiles)
    else:
        # nos quedamos con el primero
        prim = decomp.split()[0]
        res = unichr(int(prim, 16))

    # guardamos en el caché y volvemos
    _cache[car] = res
    return res


def normaliza(frase):
    '''Recibe una frase y devuelve sus palabras ya normalizadas.'''
    print "\n=========", frase
    frase = frase.lower()
    newpals = []
    for pal in set(frase.split()):
        print "== 1", pal
        newpal = u"".join(_norm_car(c) for c in pal)
        print "== 2", newpal
        newpals.append(newpal.encode("utf8")) # shelve no soporta unicode
    return newpals

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
        for palabra, docids in sorted(self.word_shelf.items()):
            print "%s: %s" % (palabra, [id_shelf[str(x)][1] for x in docids])

    def listado_completo(self):
        '''Devuelve la info de todos los artículos.'''
        return sorted(self.id_shelf.values())

    def get_random(self):
        '''Devuelve un artículo al azar.'''
        return random.choice(self.id_shelf.values())

    def search(self, words):
        '''Busca palabras completas en el índice.'''
        result = None
        for word in normaliza(words):
            if word in self.word_shelf:
                docids = self.word_shelf[word]

                # first time, create with found, else the intersection
                # of previously found with what is found now
                if result is None:
                    result = set(docids)
                else:
                    result.intersection_update(set(docids))

        if result is None:
            return []
        return [self.id_shelf[str(x)] for x in result]

    def detailed_search(self, words):
        '''Busca palabras parciales en el índice.'''
        result = None
        for word in normaliza(words):
            resultword = []
            for guardada in self.word_shelf:
                if word in guardada:
                    resultword.append(guardada)
            if not resultword:
                continue

            # word forma parte de guardada
            docids = set()
            for res in resultword:
                ids = self.word_shelf[res]
                docids.update(ids)

            # first time, create with found, else the intersection
            # of previously found with what is found now
            if result is None:
                result = docids
            else:
                result.intersection_update(docids)

        if result is None:
            return []
        return [self.id_shelf[str(x)] for x in result]

    def create(self, salida, fuente):
        '''Crea los índices.'''
        # initalize own shelves
        self.open(salida)

        # fill them
        for docid, (nomhtml, titulo) in enumerate(fuente):
            if self.verbose:
                print "Agregando al índice [%r]  (%r)" % (titulo, nomhtml)
            # docid -> info final
            self.id_shelf[str(docid)] = (nomhtml, titulo)

            # palabras -> docid
            for pal in normaliza(titulo):
                # parece no andar el setdefault del shelve
#                self.word_shelf.setdefault(pal, set()).add(docid)
                if pal in self.word_shelf:
                    info = self.word_shelf[pal]
                    info.add(docid)
                    self.word_shelf[pal] = info
                else:
                    self.word_shelf[pal] = set([docid])

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

def generar(src_info, verbose):
    return _create_index(config.LOG_PREPROCESADO, config.PREFIJO_INDICE,
                                    dirbase=src_info, verbose=verbose)

def _create_index(fuente, salida, max=None, dirbase="", verbose=False):
    # lo importamos acá porque no es necesario en producción
    from src import utiles

    if max is not None:
        max = int(max)

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
            else:
                titulo = ""
                print "WARNING: Archivo no encontrado:", nomreal

            # si tenemos max, lo respetamos y entregamos la info
            if max is not None and i > max:
                raise StopIteration
            yield (nomhtml, titulo)

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
