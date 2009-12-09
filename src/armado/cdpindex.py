# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py para consulta, se utiliza directamente
para crear el índice.
"""

import time
import sys
import os
import codecs
import config
import Queue
import threading

from .lexer import texto_a_lexemas, STOPWORDS, STOPWORDS_TITLE
from .easy_index import Index
from .prop_extract import propertiesFromHTML

usage = """Indice de títulos de la CDPedia

Para generar el archivo de indice hacer:

  cdpindex.py fuente destino [max] [dirbase]

    fuente: archivo con los títulos
    destino: en donde se guardará el índice
    max: cantidad máxima de títulos a indizar
    dirbase: de dónde dependen los archivos
"""

def leerHTML(arch):
    return codecs.open(arch, "r", "utf8").read()


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
        return self.ready.is_set()

    def run(self):
        """Levanta el índice."""
        self.indice = Index(self.directory)
        self.ready.set()

    def listar(self):
        """Devuelve las palabras y los artículos referenciados."""
        self.ready.wait()
        for palabra, info in sorted(self.indice.items()):
            data = [x[0] for x in info] # sólo nomhtml
            yield (palabra, data)

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
        return self.indice.search(
            texto_a_lexemas(words) )

    def partial_search(self, words):
        """Busca palabras parciales en el índice."""
        self.ready.wait()
        return self.indice.partial_search(
            texto_a_lexemas(words) )


def filename2title(fname):
    """Transforma un filename en su título."""
    x = fname[:-5]
    x = normaliza(x)
    p = x.split("_")

    # a veces tenemos un nro hexa de 4 dígitos al final que queremos sacar
    if len(p[-1]) == 4:
        try:
            int(p[-1], 16)
        except ValueError:
            # perfecto, no es para sacar
            pass
        else:
            p = p[:-1]

    # el tit lo tomamos como la suma de las partes
    t = " ".join(p)
    return t


def generar_de_html(dirbase, verbose):
    # lo importamos acá porque no es necesario en producción
    from src import utiles
    from src.preproceso import preprocesar

    # armamos las redirecciones
    redirs = {}
    stopwords_title = STOPWORDS_TITLE
    with codecs.open(config.LOG_REDIRECTS, "r", "utf-8") as redirects:
        for linea in redirects:
            orig, dest = linea.strip().split(config.SEPARADOR_COLUMNAS)

            # del original, que es el que redirecciona, no tenemos título, así
            # que sacamos las palabras del nombre de archivo mismo... no es lo
            # mejor, pero es lo que hay...
            titulo = filename2palabras(orig)
            redirs.setdefault(dest, []).append((palabras, set(texto_a_lexemas(titulo, stopwords_title))))

    def gen():
        # fileNames should be sorted so that similar document ids
        # have similar document values - increasing compressibility
        # (all indices will internally generate document ids)
        fileNames = sorted(preprocesar.get_top_htmls(config.LIMITE_PAGINAS))
        
        stopwords = STOPWORDS
        stopwords_title = STOPWORDS_TITLE

        # una cola para todos
        queue = Queue.Queue(500)

        # un thread para leer archivos (con lookahead)
        def reader():
            for dir3, arch, puntaje in fileNames:
                # info auxiliar
                nomhtml = os.path.join(dir3, arch)
                nomreal = os.path.join(dirbase, nomhtml)
                if os.access(nomreal, os.F_OK):
                    html = leerHTML(nomreal)
                    if html:
                        queue.put((dir3, arch, puntaje, html))
                    del html
            
            # señalizar fin de secuencia
            queue.put(None)

        # iniciar el thread
        reader = threading.Thread(target=reader)
        reader.setDaemon(True)
        reader.start()

        # otro thread para procesarlos y alimentar al generador
        total = len(fileNames)
        done = 0
        ultdir3 = ""
        
        while True:
            # extraer html de la cola, reconocer fin de secuencia
            ent = queue.get()
            if ent is None:
                break
            dir3, arch, puntaje, html = ent
            del ent
                
            # info auxiliar
            nomhtml = os.path.join(dir3, arch)
            nomreal = os.path.join(dirbase, nomhtml)

            props = propertiesFromHTML(html)
            del html
            
            if 'title' not in props:
                print "WARNING: Archivo sin titulo", nomreal
            
            titulo = props['title']
            texto = props.get('text',u'')
            del props

            if verbose:
                print "Agregando al índice [%r]  (%r)" % (titulo, nomhtml)

            # a las palabras del título le damos mucha importancia: 50, más
            # el puntaje original sobre 1000, como desempatador
            ptje_titulo = 50 + puntaje//1000
            doctuple = (nomhtml, titulo, ptje_titulo)
            for lex in set(texto_a_lexemas(titulo, stopwords_title)):
                yield lex, doctuple

            # pasamos las palabras de los redirects también que apunten
            # a este html, con el mismo puntaje
            if arch in redirs:
                for lex, rtitulo in redirs[arch]:
                    doctuple = (nomhtml, rtitulo, ptje_titulo)
                    for lex in lex:
                        yield lex, doctuple

            del doctuple

            if config.FULL_TEXT_INDEX:
                # FIXME: Mantener un puntaje por término hiere la habilidad para
                #     mantener el índice pequeño. Por lo tanto, para los términos
                #     del cuerpo se utiliza un esquema más discreto:
                #        Si el término está entre los config.KEY_TERMS
                #     términos, es 25 + puntaje//1000, (algo debajo del título).
                #        Si en cambio está por debajo, entonces es
                #     puntaje//1000.
                #        Esto limita la cantidad de entradas para cada documento
                #     a tres (título, keyword, word).
                #
                #        Eventualmente habría que considerar agregar a la interfaz
                #     del índice un mecanismo explícito para el puntaje, cosa que
                #     el índice pueda almacenarlo de forma eficiente, independiente
                #     de los datos extra para el documento.
                all_words = {}
                all_words_get = all_words.get
                for lex in texto_a_lexemas(texto, stopwords):
                    all_words[lex] = all_words_get(lex, 0) + 1
                    
                keywords = set( [
                    lex for cant,lex in
                    sorted(
                        [ (cant,lex) for lex,cant in all_words.iteritems() ]
                    )[-config.KEY_TERMS:] ] )
                is_keyword = keywords.__contains__
                
                ptje_texto = puntaje//1000
                doctuples = {
                    False : (nomhtml, titulo, ptje_texto),
                    True  : (nomhtml, titulo, ptje_texto+25),
                }
                
                for lex in all_words:
                    yield lex, doctuples[is_keyword(lex)]
                    
                del all_words, all_words_get
                del keywords, is_keyword
                del texto, titulo
                del doctuples

            # Mostrar progreso
            if ultdir3 != dir3:
                # Progreso a stderr
                print >> sys.stderr, ('%d%%' % (done * 100 // total)), dir3.encode("utf8"), "\t\r",
                sys.stderr.flush()
                ultdir3 = dir3

            done += 1


    if not os.path.exists(config.DIR_INDICE):
        os.mkdir(config.DIR_INDICE)

    cant = Index.create(config.DIR_INDICE, gen())
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

