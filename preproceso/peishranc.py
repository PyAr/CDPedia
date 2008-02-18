#!/usr/bin/python
# -*- coding: utf-8 -*-

#para probar este modulo, hay que pasarle el path entre comillas dobles. Con las comillas simples me daba error por lo menos en windows. 
#Asi sería "c:/cdpedia/accesorios/wikifiles/...."
import sys, os, subprocess, re, urllib, config
from os.path import join, getsize

usage = """
Uso: peishranc.py

A partir de un directorio donde están almacenados los html recortados,
genermos un archivo de texto con la cantidad de referencias y tamaño
de cada artículo

"""

reenlac = re.compile("\.\.\/.*?\.html")

def main(path):
    """
    Esta funcion devuelve HASTA AHORA (TODO hay que derivarlo a un archivo de texto)
    un diccionario con nombre de articulo y cant. de referencias que tiene el mismo.

    """

    acum={}
    salida = open(config.ranking_filename, "w")
    for dirpath, dirs, archs in os.walk(path):
        for nombre in archs:
            print 'Procesando: %s/%s' % (dirpath, nombre)
            path_archivo = join(dirpath, nombre)
            for enlace in reenlac.findall(file(path_archivo).read()):
                enlace = urllib.unquote(enlace).split('/')[-1]
                if not enlace in acum:
                    acum[enlace] = [1, 0]
                else:
                    acum[enlace][0] += 1
                    
            size = getsize(path_archivo)
            if not nombre in acum:
                acum[nombre] =  [0, size]
            else:
                acum[nombre][1] = size

    for key,value in acum.iteritems():
        #print repr(value)
        info = "%s %d %d\n" % (key, value[0], value[1])
        salida.write(info)
        
    #salida.close()

"""
# queda solo para referencia futura
def main(path):
    #(...)
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
    main(config.dir_recortado)
