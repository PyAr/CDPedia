import thread
import time
import webbrowser

from config import server

def sleepAndBrowse():
    time.sleep(1)
#    webbrowser.open("http://localhost:8000/Portal%7EPortada_9ada.html")
    webbrowser.open("http://localhost:8000/search")

thread.start_new(sleepAndBrowse, ())
server.run()
print "terminado, saliendo."
