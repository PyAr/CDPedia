#!/usr/bin/env python

import threading
import webbrowser

from src.armado import server
import config

event = threading.Event()

def sleepAndBrowse():
    event.wait()
    port = server.serving_port
    webbrowser.open("http://localhost:%d/%s" % (port, config.INDEX))

threading.Thread(target=sleepAndBrowse).start()
print "Levantando el server..."
server.run(event)
print "Terminado, saliendo."
