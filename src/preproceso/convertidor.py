#!/usr/bin/python

"""
Bibioteca para achicar todas las imágenes hasta que 
ocupen un espacio determinado.
"""

import os
import Image
from subprocess import *


class Agrupador:
    def __init__(self):
        self.grupos = {}
        
    def agregar(self, grupo, cant = 1):
        if grupo not in self.grupos:
            self.grupos[grupo] = 0    
        self.grupos[grupo] += cant
                        
    def eliminar(self, grupo):
        del self.grupos[grupo]
            
    def total(self):
        total = 0
        for k, v in self.grupos.iteritems():
            total = total + k * v
        return total

    def mayor(self, pos = 0):
        ordenados = sorted(self.grupos, reverse=True)
        if len(ordenados) == 1 and pos != 0:
            return None
        else:
            return ordenados[pos]
        
    def total_grupo(self, grupo):
        return grupo * self.grupos[grupo]
        
    def cant_grupo(self, grupo):
        return self.grupos[grupo]
        
    def __str__(self):
        modelo = "%d (%d), "
        salida = ""
        for k,v in self.grupos.iteritems():
            salida += modelo % (k, v)
        return salida



def file_size(archivo):
    file_stat = os.stat(archivo)
    return int(file_stat[6] / 1024)


def get_lado_mayor(imagen):
    im = Image.open(imagen)
    print "resolucion " + str(im.size), 
    lado1, lado2 = im.size
    if lado1 > lado2:
        return lado1
    else:
        return lado2
    
def convertir(imagen_origen, imagen_destino, lado):
    im = Image.open(imagen_origen)
    im.thumbnail((lado, lado), Image.ANTIALIAS)
    im.save(imagen_destino)



def acotar(imagen, max_size, steps = 50):
    print "achicando a " + str(max_size) + "Kb",

    paso = 1.0 / steps
    img_size = file_size(imagen)
    aux_img = os.tempnam('./') + ".jpg"

    lado = get_lado_mayor(imagen)

    i = 1
    escala = int(lado * (1 - (paso * i)))    
    while img_size > max_size and escala > 0:
        print str(escala) + "x" + str(escala),
        convertir(imagen, aux_img, escala)
        img_size = file_size(aux_img)
        i = i + 1
        escala = int(lado * (1 - (paso * i)))

    print "ok"                   
    os.rename(aux_img, imagen)


def busca_max_size(maximo_total):
    max_file_size = 0
    archivos = Agrupador()
    
    for archivo in os.listdir(os.curdir):
        archivos.agregar(file_size(archivo))

    size_actual = archivos.total()
    
    while size_actual > maximo_total:
        print str(archivos)
        print size_actual, max_file_size

        sobran = size_actual - maximo_total
        
        mayor = archivos.mayor()
        total_mayor = archivos.total_grupo(mayor)
        cant_mayor = archivos.cant_grupo(mayor)
        
        prox_grupo = archivos.mayor(1)
        if prox_grupo is None:
            prox_grupo = maximo_total / cant_mayor
            nuevo_grupo = prox_grupo
            size_actual = maximo_total
        else:
            nuevo_grupo = max((total_mayor - sobran) / cant_mayor, prox_grupo)
            archivos.agregar(nuevo_grupo, cant_mayor)
            archivos.eliminar(mayor)
            size_actual = archivos.total()

        max_file_size = nuevo_grupo
    
    return max_file_size



if __name__ == "__main__":
    maximo = 2500
    max_file_size = busca_max_size(maximo)
    print max_file_size

    if max_file_size > 0:
        for imagen in os.listdir(os.curdir):
            print imagen ,

            img_size = file_size(imagen)
            if img_size > max_file_size:
                acotar(imagen, max_file_size)
            else:
                print "ok"
