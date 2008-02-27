import server
import thread
import time
import webbrowser

def sleepAndBrowse():
    time.sleep(3)
    webbrowser.open("http://localhost:8000/Portal%7EPortada_9ada.html")

thread.start_new(sleepAndBrowse, ())
server.run()
print "terminado, saliendo."
