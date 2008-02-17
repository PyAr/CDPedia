# -*- coding: utf-8 -*-

import sys, os, subprocess, re, urllib

usage = """
Usar: peishranc.py <nombre_archivo>

   donde el archivo es el dump de la wikipedia comprimida con 7z

      ej: "peishranc.py wikipedia-es-html.7z"

   El programa tira la lista y porcentajes a stdout
"""

PASOSHOW = 1000
CARAJO = open('/dev/null', 'w')

def getLineas(nomarch):
    p = subprocess.Popen(("7z l %s" % nomarch).split(), stdout=subprocess.PIPE)
    util = False
    for lin in p.stdout:
        esguion = lin.strip().replace(" ","")
        if esguion and esguion == "-"*len(esguion):
            if util:  # encontramos la segunda, terminamos
                break  
            else:     # encontramos la primera, ahora pasamos a ser utiles
                util = True
                continue
        if not util:
            continue

        lin = lin.split()
        tamanio = int(lin[3])
        fname = os.path.basename(lin[-1])
        yield (tamanio, fname)


class GetArchs(object):
    def __init__(self, nomarch):
        self.p = subprocess.Popen(("7z e -so %s" % nomarch).split(), stdout=subprocess.PIPE, stderr=CARAJO)

    def __call__(self, largo):
        return self.p.stdout.read(largo)

reenlac = re.compile("\.\.\/.*?\.html")
#reenlac = re.compile("def .*:")

def main(nomarch):
    print "Analizando %r..." % nomarch
    pasoant = 0
    total = 0
    garchs = GetArchs(nomarch)
    acum = {}
    for (tamanio, nombre) in getLineas(nomarch):
        # vamos mostrando de a tantos
        total += 1
        if total // PASOSHOW > pasoant:
            sys.stdout.write("\r%d...     " % total)
            sys.stdout.flush()
            pasoant = total // PASOSHOW
        
        arch = garchs(tamanio)

        for enlace in reenlac.findall(arch):
            enlace = urllib.unquote(enlace)
            acum[enlace] = acum.get(enlace, 0) + 1

                
    print "\nMostrando los resultados para un total de %d archivos\n" % total
    maslargo = max([len(x) for x in acum.keys()])
    for nombre,cant in sorted(acum.items(), key=lambda x: x[1], reverse=True)[:30]:
        print "  %s  %7d" % (nombre.ljust(maslargo), cant)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit(1)

    main(sys.argv[1])

