#!/usr/bin/env python
# -- coding: utf8 --

import threading
import webbrowser
import os
import sys
import traceback

# fix path if needed
if os.path.exists("cdpedia"):
    sys.path.append("cdpedia")

from src.armado import server
from src.utiles import WatchDog
import config

server_up = threading.Event()
browser_up = threading.Event()

# WatchDog timer
wd_timer = None

# Tiempo entre llamadas a cd_watch_dog en segundos
CD_WD_SECONDS = 10

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

def cd_watch_dog():
    ''' Comprueba que el CD está puesto '''
    global wd_timer

    try:
        archivos = os.listdir('.')
    except OSError:
        # El CD no esta disponible
        close()

    if not 'cdpedia.py' in archivos:
        # El CD no es CDPedia
        close()

    # Sigue andando, probemos mas tarde
    wd_timer = threading.Timer(CD_WD_SECONDS, cd_watch_dog)
    wd_timer.start()

def sleep_and_browse():
    global wd_timer
    server_up.wait()
    port = server.serving_port
    wd_timer = threading.Timer(CD_WD_SECONDS, cd_watch_dog)
    wd_timer.start()
    if config.EDICION_ESPECIAL is None:
        index = "http://localhost:%d/%s" % (port, config.INDEX)
    else:
        index = "http://localhost:%d/%s/%s" % (port, config.EDICION_ESPECIAL,
                                                                config.INDEX)
    webbrowser.open(index)
    browser_up.set()


def start_browser_watchdog():
    browser_up.wait()
    browser_watchdog.start()


threading.Thread(target=sleep_and_browse).start()

browser_watchdog = WatchDog(callback=close, sleep=config.BROWSER_WD_SECONDS)
threading.Thread(target=start_browser_watchdog).start()

print "Levantando el server..."
server.run(server_up, browser_watchdog.update)
print "Terminado, saliendo."
wd_timer.cancel()
