#!/usr/bin/env python
# -- coding: utf8 --

import threading
import webbrowser
import os
import sys
import traceback

from src.armado import server
import config

event = threading.Event()

# WatchDog timer
wd_timer = None

# Tiempo entre llamadas a watch_dog en segundos
WD_SECONDS = 10

def handle_crash(type, value, tb):
    '''Function to handle any exception that is not addressed explicitly.'''
    if issubclass(type, KeyboardInterrupt):
        # Nos vamos!
        wd_timer.cancel()
        sys.exit(0)
    else:
        exception = traceback.format_exception(type, value, tb)
        exception = "".join(exception)
        print exception

sys.excepthook = handle_crash

def close():
    ''' Cierra el servidor y termina cdpedia '''
    server.shutdown()
    sys.exit(0)

def watch_dog():
    ''' Comprueba que el CD está puesto '''
    global wd_timer

    try:
        archivos = os.listdir('.')
    except OSError:
        # El CD no esta disponible
        close()

    if not 'main.py' in archivos:
        # El CD no es CDPedia
        close()

    # Sigue andando, probemos mas tarde
    wd_timer = threading.Timer(WD_SECONDS, watch_dog)
    wd_timer.start()

def sleep_and_browse():
    global wd_timer
    event.wait()
    port = server.serving_port
    wd_timer = threading.Timer(WD_SECONDS, watch_dog)
    wd_timer.start()
    webbrowser.open("http://localhost:%d/%s" % (port, config.INDEX))

threading.Thread(target=sleep_and_browse).start()
print "Levantando el server..."
server.run(event)
print "Terminado, saliendo."
