import sys, codecs
sys.path.append("/data/test")
from mwlib import htmlwriter, uparser, dummydb

def main(titulo, archin, archout):
    out = codecs.open(archout, "w", "utf8")

    inp = codecs.open(archin, "r", "utf8")
    article = inp.read()
    inp.close()

    p = uparser.parseString(titulo, raw=article, wikidb=dummydb.DummyDB())

    w = htmlwriter.HTMLWriter(out)
    w.write(p)
    out.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Usar  %s titulo input.xml output.html" % sys.argv[0]
        sys.exit()
    main(*sys.argv[1:])
