# -*- coding: utf8 -*-

'''Algunas pequeñas funciones útiles.'''

import re
import time
import threading

import config

if hasattr(config, 'NAMESPACES'):
    # coincide si se empieza con uno de los namespaces más ~
    RE_NAMESPACES = re.compile(r'(%s):(.*)' % '|'.join(config.NAMESPACES))

def separaNombre(nombre):
    '''Devuelve (namespace, resto) de un nombre de archivo del wiki.'''
    m = RE_NAMESPACES.match(nombre)
    if not m:
        result = (None, nombre)
    else:
        result = m.groups()
    return result


class WatchDog(threading.Thread):
    """Implementa un watchdog usando un thread.

    Una vez iniciado el watchdog se debe llamar al método update periódicamente a
    intervalos menores a sleep segundos para prevenir que el watchdog termine y
    llame al callback.

    En esta simple implementación el callback puede tardar hasta 2 veces sleep
    segundos en ser llamado.
    """
    def __init__(self, callback, sleep):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.callback = callback
        self.sleep = sleep
        self._tick = False

    def update(self):
        self._tick = False

    def run(self):
        while True:
            if self._tick:
                break
            self._tick = True
            time.sleep(self.sleep)
        self.callback()

