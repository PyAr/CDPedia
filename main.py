import thread
import time
import webbrowser

from config import server

def sleepAndBrowse():
    time.sleep(1)
    webbrowser.open("http://localhost:8000/")

thread.start_new(sleepAndBrowse, ())
server.run()
print "terminado, saliendo."
