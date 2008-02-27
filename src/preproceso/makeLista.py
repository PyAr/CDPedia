# -*- coding: utf-8 -*-

import sys, os, subprocess

usage = """
Usar: makeLista.py <nombre_archivo>

   donde el archivo es el dump de la wikipedia comprimida con 7z

      ej: "makeLista.py wikipedia-es-html.7z"

   El programa tira la lista y porcentajes a stdout
"""

PASOSHOW = 1000

def main(nomarch):
    total = tamtotal = 0
    acum = {}
    print "Analizando %r..." % nomarch
    p = subprocess.Popen(("7z l %s" % nomarch).split(), stdout=subprocess.PIPE)
    util = False
    pasoant = 0
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
        tamtotal += tamanio
        fname = os.path.basename(lin[-1])

        if total // PASOSHOW > pasoant:
            sys.stdout.write("\r%d...     " % total)
            sys.stdout.flush()
            pasoant = total // PASOSHOW
        
        if "~" in fname:
            raiz = fname.split("~")[0].decode("utf-8")
        else:
            raiz = "None"

        (cant, tam) = acum.get(raiz, (0,0))
        cant += 1
        tam += tamanio
        acum[raiz] = (cant, tam)
        total += 1
                
    print "\nMostrando los resultados para un total de %d archivos que ocupan %.2f MB:\n" % (total, tamtotal/1048576.0)
    maslargo = max([len(x) for x in acum.keys()])
    print "  %s    Cant      Cant%%  Tamaño   Tamaño%%" % "Raiz".ljust(maslargo)
    for (raiz, (cant,tam)) in sorted(acum.items(), key=lambda x: x[1][1], reverse=True):
        tammb = tam/1048576.0
        if tammb < 1:
            break
        print "  %s  %7d  %8.2f%%  %3d MB  %7.2f%%" % (raiz.ljust(maslargo), cant, 100*cant/float(total), tammb, 100*tam/float(tamtotal))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit(1)

    main(sys.argv[1])

