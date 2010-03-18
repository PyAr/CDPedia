#!/usr/bin/env python

import threading
import webbrowser

from src.armado import server

event = threading.Event()

def sleepAndBrowse():
    event.wait()
    port = server.serving_port
    webbrowser.open("http://localhost:%d/" % port)

threading.Thread(target=sleepAndBrowse).start()
print "Levantando el server..."
server.run(event)
print "Terminado, saliendo."
