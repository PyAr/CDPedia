    #geany
    #Esta funcion recibe como parametros la ruta completa del Makespec.py 
    #La carpeta donde se quiere poner el ejecutable que se va a crear.
    #Y por ultimo el nombre del archivo que se va a crear. 
    #tener en cuenta que se utiliza pyinstaller para realizar el ejecutable.
    #admas le agregaria otro parametro para que se puedan setear por parametros el resto de los atributos.
import os
def main():
    strCarpetaPyInstaller = 'C:/wikipediaOffLine/pyinstaller-1.3/'
    parametros = '-D -a -c '
    strCarpetaSalida = 'F:' 
    strNombreExe = 'WikipediaOffLine'
    strArchivoEntrada = 'C:/wikipediaOffLine/aplicacion/launch.py'  
    os.system (strCarpetaPyInstaller + 'Makespec.py ' + parametros + ' -o ' + strCarpetaSalida + ' -n ' + strNombreExe + ' ' + strArchivoEntrada)
    os.system (strCarpetaPyInstaller + 'Build.py ' + strCarpetaSalida + '/' + strNombreExe + '.spec ' + strNombreExe)
    
main()