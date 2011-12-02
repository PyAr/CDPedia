#!/usr/bin/env python
# -- coding: utf8 --

import os
import sys
import codecs
import platform
import optparse
import threading
import traceback
import webbrowser

# fix path if needed
if os.path.exists("cdpedia"):
    sys.path.append("cdpedia")

# Logeamos stdout y stderr si estamos en windows
if platform.system() == 'Windows':
    log_filename = os.path.join(os.path.expanduser('~'), 'cdpedia.log')
    try:
        log = codecs.open(log_filename, 'w', 'utf8', errors='replace')
        sys.stdout = log
        sys.stderr = log
    except:     # Si no podemos logear ni mostrar el error porque no
        pass    # tenemos una consola no podemos hacer nada.

from src import third_party # Need this to import thirdparty (werkzeug and jinja2)
from werkzeug.serving import ThreadedWSGIServer
from src.utiles import WatchDog, find_open_port
from src.web.web_app import create_app
import config


def handle_crash(type, value, tb):
    '''Function to handle any exception that is not addressed explicitly.'''
    if issubclass(type, KeyboardInterrupt):
        # Nos vamos!
        cd_wd_timer.cancel()
        sys.exit(0)
    else:
        exception = traceback.format_exception(type, value, tb)
        exception = "".join(exception)
        print exception

def close():
    ''' Cierra el servidor y termina cdpedia '''
    server.shutdown()
    sys.exit(0)

def cd_watch_dog():
    ''' Comprueba que el CD está puesto '''
    global cd_wd_timer

    try:
        archivos = os.listdir('.')
    except OSError:
        # El CD no esta disponible
        close()

    if not 'cdpedia.py' in archivos:
        # El CD no es CDPedia
        close()

    # Sigue andando, probemos mas tarde
    cd_wd_timer = threading.Timer(CD_WD_SECONDS, cd_watch_dog)
    cd_wd_timer.daemon = True
    cd_wd_timer.start()

def sleep_and_browse():
    server_up.wait()
    if config.EDICION_ESPECIAL is None:
        index = "http://%s:%d/" % (config.HOSTNAME, config.PORT)
    else:
        index = "http://%s:%d/%s/%s" % (config.HOSTNAME, config.PORT,
                                        config.EDICION_ESPECIAL, config.INDEX)
    webbrowser.open(index)

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", default=False,
                  dest="verbose", help="muestra info de lo que va haciendo")
    parser.add_option("-d", "--daemon", action="store_true", default=False,
                  dest="daemon", help="daemonize server")
    parser.add_option("-p", "--port", type="int", dest="port",
                      default=config.PORT)
    parser.add_option("-m", "--host", type="str", dest="hostname",
                      default=config.HOSTNAME)
    (options, args) = parser.parse_args()

    sys.excepthook = handle_crash

    if options.daemon:
        port = options.port
    else:
        port = find_open_port(starting_from=options.port, host=options.hostname)

    config.PORT, config.HOSTNAME = port, options.hostname

    if not options.daemon:
        server_up = threading.Event()

        # CD WatchDog timer
        cd_wd_timer = None

        # Tiempo entre llamadas a cd_watch_dog en segundos
        CD_WD_SECONDS = 10

        cd_wd_timer = threading.Timer(CD_WD_SECONDS, cd_watch_dog)
        cd_wd_timer.daemon = True
        cd_wd_timer.start()

        threading.Thread(target=sleep_and_browse).start()

        browser_watchdog = None
        if config.BROWSER_WD_SECONDS:
            browser_watchdog = WatchDog(callback=close, sleep=config.BROWSER_WD_SECONDS)
            # Iniciamos el watchdog por más que aún no esté levantado el browser ya que
            # el tiempo del watchdog es mucho mayor que el que se tarda en levantar el server
            # y el browser.
            browser_watchdog.start()

        if options.verbose:
            print "Levantando el server..."

        app = create_app(browser_watchdog, verbose=options.verbose)

        server = ThreadedWSGIServer(config.HOSTNAME, config.PORT, app, handler=None,
                                    passthrough_errors=False)
        server_up.set()
        server.serve_forever()

        if options.verbose:
            print "Terminado, saliendo."
        cd_wd_timer.cancel()

    else:
        app = create_app(watchdog=None, verbose=options.verbose)
        server = ThreadedWSGIServer(config.HOSTNAME, port, app, handler=None,
                                    passthrough_errors=False)
        server.serve_forever()
