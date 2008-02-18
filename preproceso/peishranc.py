# -*- coding: utf-8 -*-
#para probar este modulo, hay que pasarle el path entre comillas dobles. Con las comillas simples me daba error por lo menos en windows. 
#Asi sería "c:/cdpedia/accesorios/wikifiles/...."
import sys, os, subprocess, re, urllib, codecs
from os.path import join, getsize

usage = """
Usar: peishranc.py <nombre_archivo>

   donde el archivo es el dump de la wikipedia comprimida con 7z

      ej: "peishranc.py wikipedia-es-html.7z"

   El programa tira la lista y porcentajes a stdout
"""

PASOSHOW = 1000
CARAJO = open('/dev/null', 'w')

def getLineas(nomarch):
    #Ya no es necesario, dado que cambio la forma de entrada. No es mas un 7z, sino que vamos a trabajar con los archivos ya descomprimidos.
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
    #Ya no es necesario, dado que cambio la forma de entrada. No es mas un 7z, sino que vamos a trabajar con los archivos ya descomprimidos.
    def __init__(self, nomarch):
        self.p = subprocess.Popen(("7z e -so %s" % nomarch).split(), stdout=subprocess.PIPE, stderr=CARAJO)

    def __call__(self, largo):
        return self.p.stdout.read(largo)

reenlac = re.compile("\.\.\/.*?\.html")

def getReferencias(path):
    #Esta funcion devuelve HASTA AHORA (TODO hay que derivarlo a un archivo de texto) un diccionario con nombre de articulo y cant. de referencias que tiene el mismo.
    acum={}
    f = open("preproceso/refList.txt","w")
    print 'Se comienza a contar las referencias, teniendo en cuenta la carpeta: ' + path
    for dirpath, dirs, archs in os.walk(path):
        break
        for nombre in archs:
            for enlace in reenlac.findall(file(join(dirpath, nombre)).read()):
                enlace = urllib.unquote(enlace).split('/')
                acum[enlace[-1]] = acum.get(enlace[-1], 0) + 1
    tam={}
    print 'Se comienza a buscar el peso de los archivos, teniendo en cuenta la carpeta: ' + path
    for dirpath, dirs, archs in os.walk(path):
        for nombre in archs:
            if not nombre in acum.keys():
                acum[nombre] = 0
            acum[nombre] = [acum[nombre],getsize(join(dirpath, nombre))]

    for key,value in acum.iteritems():
        info= "%s %d %d" % (key,value[0],value[1])
        f.write(info+"\n")
    f.close()


def getTamanios(path):
    #Esta funcion devuelve HASTA AHORA (TODO hay que derivarlo a un archivo de texto) un diccionario con nombre de articulo y tamanio del mismo.
    tam={}
    print 'Se comienza a buscar el peso de los archivos, teniendo en cuenta la carpeta: ' + path
    for dirpath, dirs, archs in os.walk(path):
        for nombre in archs:
            tam[nombre] = getsize(join(dirpath, nombre))
        print type(tam),"TAMANIOTAMANIOTAMANIO"
        
    #esto habria que bajarlo a un archivo de texto, para que no sea necesario volver a procesar cuando se quieran aplicar estas metricas.

def main(path):
    getReferencias(path)
    #getTamanios(path)

    """
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
    """

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print usage
        sys.exit(1)
    main(sys.argv[1])
