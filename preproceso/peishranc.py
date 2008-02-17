# -*- coding: utf-8 -*-

import sys, os, subprocess, re, urllib

"""
	Metricas a aplicar para determinar el valor de una pagina.
	1.Cantidad de referencias. Ver como se pondera despues.
	2.Tamanio de la pagina. Ver como se pondera despues.
"""
usage = """
Usar: peishranc.py <nombre_archivo>

   donde el archivo es el dump de la wikipedia comprimida con 7z

      ej: "peishranc.py wikipedia-es-html.7z"

   El programa tira la lista y porcentajes a stdout
"""

PASOSHOW = 1000
CARAJO = open('c:/wikipediaOffLine/Error.txt', 'w')

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

def getReferencias(objLineas, nomarch, acum):
    print "Analizando referencias %r..." % nomarch
    pasoant = 0
    total = 0
    garchs = GetArchs(nomarch)
    for (tamanio, nombre) in objLineas:
        # vamos mostrando de a tantos
        total += 1
        if total // PASOSHOW > pasoant:
            sys.stdout.write("\r%d...     " % total)
            sys.stdout.flush()
            pasoant = total // PASOSHOW
        arch = garchs(tamanio)
        for enlace in reenlac.findall(arch):
            enlace = urllib.unquote(enlace).split('/')      #con el split y el [-1] de la linea de abajo, lo que hacemos es sacar la mugre de las referencias absolutas de una pagina.
            acum[enlace[-1]] = acum.get(enlace[-1], 0) + 1
        if total > 10000:
            return
    return

def main(nomarch):
    total = 0
    lineas = getLineas(nomarch) #De aca se va a obtener nombre y tamanio del articulo
    acum = {}
    getReferencias(lineas, nomarch, acum)   #De aca se va a obtener nombre y cantidad de referencias.
    dicFinal = {}
    for (tamanio, nombre) in lineas:
        dicFinal[nombre] = (acum.get(nombre,0),tamanio)
    dicFinal = filter(lambda x:(x[1][0] > 1000), dicFinal.items())
    #dicFinal = sorted(dicFinal, key=lambda x: x[1][1], reverse=True)
    dicFinal.sort(key=lambda x: x[1][1], reverse=True)
    i=0
    while (total < 600*1024*1024) and i < len(dicFinal):
        total += dicFinal[i][1][1]
        print dicFinal[i]
        i+=1
        

#def filterReferencias():
#    return (x[1][0] > 5)
   
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit(1)

    main(sys.argv[1])

