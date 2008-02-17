#!/usr/bin/env python
#
# 1. Baja el archivo de Wikipedia
# 2. Lo descomprime con el 7z
# 3. Lo limpia de los archivos que no queremos
#

import os, re
import sys, urllib, urllib2, time
import config
import subprocess

def limpiaTodo(directorio):
    # deberia dar algo como... "(Usuario.*|Imagen.*|Discusi.*|MediaWiki.*|Plantilla.*)~.*"
    target = "(%s)~.*" % "|".join([x+".*" for x in config.palabras])
    print "  Borrando segun la siguiente regexp:", target

    reMacheo = re.compile (target)
    borrados = open(config.logborrado, "w")
    suma = 0

    for dirpath, dirnames, filenames in os.walk ("."):
        for filename in filenames:
            if reMacheo.match (filename) is not None:
                f = os.path.join (dirpath,filename)
                suma += os.stat(f).st_size
                os.unlink (f)
                borrados.write(f+"\n")
    print "  Borramos %.2f MB de archivos que no incluiremos, la lista está en '%s'" % (suma/1048576.0, config.logborrado)
    return


class Avance:
    def __init__(self, nomarch, largo):
        self.nomarch = nomarch
        self.total = 0
        self.antval = 0
        self.largo = largo
        print "  Bajando '%s' [%s KB]..." % (self.nomarch, largo/1024)

    def step(self, cant):
        self.total += cant
        pt = self.total / 1024
        if pt == self.antval:
            return
        self.antval = pt
        sys.stdout.write("\r  %7d KB" % pt)
        sys.stdout.flush()

    def done(self):
        if self.largo == self.total:
            print "\r  Terminado OK"
        else:
            print "  Terminado con Error! Largo: %s   Total: %s" % (self.largo, self.total)
        return
        
def bajar(url, archout):
    print " ", url
    
    # abrimos el archivo remoto
    u = urllib.urlopen(url)
    largo = int(u.headers["content-length"])

    # y lo bajamos
    av = Avance(archout, largo)
    aout = open(archout, "wb")
    while True:
        r = u.read(4096)
        if r == "":
            break
        aout.write(r)
        av.step(len(r))
    av.done()
    return



def main():
    # baja el archivo
    nomarch = "wikipedia-%s-html.7z" % config.idioma
    if os.access(nomarch, os.F_OK):
        print "Warning - El archivo %r ya existe, omitimos bajarlo" % nomarch
    else:
        print "Bajando el archivo %r..." % nomarch
        bajar(config.urlwikipedia + nomarch, nomarch)

    
    retcode = subprocess.call("7z x %s"%nomarch, shell=True)
    if retcode:
        print "Hubo un problema al descomprimir, 7z devolvió %r" % retcode
        sys.exit(1)
    
    # lo limpia todo
    limpiaTodo("./%s" % config.idioma)

    # y lo recomprime
    nomzip = "%s.zip"%config.idioma
    retcode = subprocess.call("zip -r -9 %s %s"%(nomzip, config.idioma),shell=True)
    if retcode < 0:
        print "Hubo un problema al recomprimir, zip devolvió %r" % retcode
        sys.exit(1)
    return

if __name__ == "__main__":
    main()
