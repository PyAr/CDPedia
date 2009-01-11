# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py para consulta, se utiliza directamente
para crear el índice.
"""

#from __future__ import division
import shelve, time, sys, os.path, re, codecs
import config

usage = """Indice de títulos de la CDPedia

Para generar el archivo de indice hacer:

  cdpindex.py fuente destino [max] [dirbase]

    fuente: archivo con los títulos
    destino: en donde se guardará el índice
    max: cantidad máxima de títulos a indizar
    dirbase: de dónde dependen los archivos
"""

#def getsubstrings(source, minim=3):
#    for size in range(minim, len(source)+1):
#        for pos in range(0, len(source)-size+1):
#            yield source[pos:pos+size]

# Buscamos todo hasta el último guión no inclusive, porque los
# títulos son como "Zaraza - Wikipedia, la enciclopedia libre"
SACATIT = re.compile(".*?<title>([^<]*)\s+-", re.S)

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

# Esto es porque shelve NO soporte unicode en las keys, veremos que hacemos luego
#import cPickle
#class MyShelve(dict):
#    def __init__(self, filename):
#        self.filename = filename
#    def close(self):
#        f = open(self.filename, "w")
#        cPickle.dump(self)

class Index(object):
    def __init__(self, filename=None):
        if filename is not None:
            self.open(filename)

    def listar(self):
        id_shelf = self.id_shelf
        for palabra, docids in sorted(self.word_shelf.items()):
            print "%s: %s" % (palabra, [id_shelf[str(x)][1] for x in docids])

    def search(self, words):
        result = None
        words = words.encode("utf8") # shelve no soporta unicode
        words = words.lower().split()
        for word in words:
            resultword = set()
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


    def create(self, salida, fuente):
        # initalize own shelves
        self.open(salida)

        # fill them
        for docid, (nomhtml, titulo) in enumerate(fuente):
            print "Agregando al índice [%r]  (%r)" % (titulo, nomhtml)
            # docid -> info final
            self.id_shelf[str(docid)] = (nomhtml, titulo)

            # palabras -> docid
            titulo = titulo.encode("utf8") # shelve no soporta unicode
            titulo = titulo.lower()
            pals = set(titulo.split())
            for pal in pals:
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

#    def index(self, item, description):
#        iid = hash(item)
#        self.id_shelf[ str(iid) ] = item,description
#        parts = description.split(":")
#        result = []
#        for p in parts:
#            result += p.split(" ")
#
#        result = [ w.lower() for w in result ]
#        result = set(result)
#        words = set(result)
#        for w in result:
#            res = list(getsubstrings(w))
#            words.update(res)
#
#        for word in words:
#            s = self.word_shelf.get(word, set())
#            s.add( iid )
#            self.word_shelf[word]=s

#    def flush(self):
#        self.word_shelf.sync()
#        self.id_shelf.sync()

    def open(self, filename):
        wordsfilename = filename + ".words"
        idsfilename = filename + ".ids"
        print "Opening", wordsfilename
        self.word_shelf = shelve.open(wordsfilename)
        print "Opening", idsfilename
        self.id_shelf = shelve.open(idsfilename)

#    def save(self):
#        if self.todisk:
#            self.flush()
#        else:
#            wshelf = self.word_shelf
#            ishelf = self.id_shelf
#            self.open()
#            print "Updating word shelf"
#            self.word_shelf.update(wshelf)
#            print "Updating id shelf"
#            self.id_shelf.update(ishelf)
#            print "Syncing"
#            self.flush()
#            print 'Done'

def generar(src_info):
    _create_index(
            config.LOG_PREPROCESADO, config.PREFIJO_INDICE, dirbase=src_info)

def _create_index(fuente, salida, max=None, dirbase=""):
    if max is not None:
        max = int(max)

    index = Index()

    def fix(letra):
        if letra == " ":
            letra = "_"
        return letra

    def get3letras(arch):
        arch = arch[:-5] # le sacamos el .html
        arch = arch.lower()
        arch = (arch+"   ")[:3] # nos quedamos con las primeras 3 llenando con espacios
        return map(fix, arch)

    def gen():
        fh = codecs.open(fuente, "r", "utf8")
        fh.next() # título
        for i,linea in enumerate(fh):
            arch = linea.split()[0].strip()
            if not arch.endswith(".html"):
                continue

            print "Indizando [%d] %s" % (i, arch.encode("utf8"))
            # info auxiliar
            a,b,c = get3letras(arch)
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


#    parsed_file = "parsed/parsefile.cpkl"
#
#    print "Opening Index:", indexfilename
#    index = cdpindex.Index(indexfilename)
#    print "Opening contents:", zipfilename
#    wikipedia = zipfile.ZipFile(zipfilename)
#    print "Stage 1:"
#    try:
#        f = open(parsed_file)
#        print "Loading parsed pages"
#        all = cPickle.load(f)
#    except IOError:
#        print "Creating parsed pages"
#        timer = Timer()
#        print "Generating namelist"
#        namelist = list(wikipedia.namelist())
#        total = len(namelist)
#        print "Done with namelist"
#        timer.start(len(namelist))
#        all = []
#        for i,name in enumerate(namelist):
#            if maxitems and i>maxitems: break
#            if i%50==0:
#                timer.tick(50)
#
#            if name.endswith(".html"):
#                title = gettitle(wikipedia, name)
#                all.append( (name, title) )
#        cPickle.dump( all, open(parsed_file, "w") )
#    print "Done."
#
#    timer = Timer()
#    timer.start(len(all))
#    for i,(name, title) in enumerate(all):
#        if maxitems and i>maxitems: break
#        if i%50==0:
#            timer.tick(50)
#        if name.endswith(".html"):
#            index.index(name, title)
#        if i%50==0:
#            index.flush()
#    index.save()
#    print "Exiting..."

