import threading
import webbrowser

from src.armado import server

event = threading.Event()

def sleepAndBrowse():
    event.wait()
    webbrowser.open("http://localhost:8000/")

threading.Thread(target=sleepAndBrowse).start()
print "Levantando el server..."
server.run(event)
print "Terminado, saliendo."
