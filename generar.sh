# Falta: script que se fije si bajamos o no el 7z y si borramos lo que teníamos antes
time python preproceso/preprocesar.py
#python preproceso/seleccion.py

# armar los bloques comprimidos
rm salida/bloques/*.cdp
time python armado/compresor.py

# armar el ejecutable para win32
