# -*- coding: utf-8 -*-

# Copyright 2010-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/


import queue
import threading
import time

# cuanto duerme para que el while no mate el procesador
SLEEP = .3


class _Trabajador(threading.Thread):
    """Clase que usa el repartidor internamente.

    Ejecuta una función recibida de afuera.
    """
    def __init__(self, nro, funcion, colaInput, colaOutput, termine):
        self.yo = nro
        self.funcion = funcion
        self.cinp = colaInput
        self.cout = colaOutput
        self.termine = termine
        threading.Thread.__init__(self)

    def run(self):
        while True:
            info = self.cinp.get()
            if info == "quit":
                break
            res = self.funcion(info)
            self.termine.set()
            self.cout.put((info, res))


class Pool(object):
    """Arma un pool de hilos para repartir tareas.

    @param funcion: funcion a ejecutar
    @param cant: cantidad de trabajadores a abrir
    @param logf: funcion para loguear mensajes
    """
    def __init__(self, funcion, cant, logf=None):
        self._cantw = cant
        if logf is None:
            self.logf = lambda x: None
        else:
            self.logf = logf

        # lanzamos los n hilos para cada destino
        self.qEnviar = [queue.Queue() for x in range(self._cantw)]
        self.qRecbir = [queue.Queue() for x in range(self._cantw)]
        self.eTermin = [threading.Event() for x in range(self._cantw)]
        for i in range(self._cantw):
            h = _Trabajador(i, funcion, self.qEnviar[i], self.qRecbir[i], self.eTermin[i])
            h.start()
        self.logf("Se crearon %d hilos" % (cant,))

    def procesa(self, trabajos):
        """Procesa los trabajos recibidos.

        Los desparrama entre los trabajadores, en paralelo, mientras estén
        libres.  Va entregando los resultados como generador, siempre con el
        payload al principio.

        @param trabajos: todos los trabajos
        """

        # preparamos
        encolados = trabajos[:]
        encolados.reverse()
        disponibles = [True] * self._cantw

        # ejecutamos mientras tengamos encolados pendientes o haya un destino
        # sin terminar
        while encolados or sum(disponibles) < self._cantw:
            self.logf("Hay encolados (%d) o estamos esperando algun "
                      "trabajo (%r)" % (len(encolados), disponibles))

            # si hay algún hilo libre le damos trabajo (si hay)
            while (encolados and (True in disponibles)):
                payload = encolados.pop()
                libre = disponibles.index(True)
                q = self.qEnviar[libre]
                q.put(payload)
                disponibles[libre] = False
                self.logf("Enviamos %r al hilo %d" % (payload, libre))

            # revisamos los pendientes, para ver si terminó alguno
            for i in range(self._cantw):
                if not self.eTermin[i].isSet():
                    continue

                # tenemos un dato de alguno
                result = self.qRecbir[i].get()
                self.eTermin[i].clear()
                self.logf("Recibimos %r del hilo %d" % (result, i))
                yield result
                disponibles[i] = True

            # dormimos para que el while no me ocupe todo el procesador
            time.sleep(SLEEP)

        for q in self.qEnviar:
            q.put("quit")
        self.logf("Se envio quit a todos los hilos")
