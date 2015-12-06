#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uso: preprocesar.py

Aplica los procesadores definidos en preprocesadores a cada
una de las páginas, para producir la prioridad con la que página
será (o no) incluída en la compilación.

"""

from __future__ import with_statement

import os
import codecs
import config
import logging
import operator

from os.path import join, abspath, dirname

from src.preproceso import preprocesadores
from src import utiles

logger = logging.getLogger('preprocesar')


class WikiArchivo(object):
    def __init__(self, cwd, ult3dirs, nombre_archivo):
        self.ruta_relativa = join(ult3dirs, nombre_archivo)
        self.url = nombre_archivo
        self._filename = join(cwd, nombre_archivo)
        self._html = None

    def get_html(self):
        """Devuelve el contenido del archivo, lo carga si no lo tenía."""
        if self._html is None:
            with open(self._filename, 'rb') as fh:
                self._html = fh.read()

        return self._html

    def set_html(self, data):
        """Setea el html."""
        self._html = data

    html = property(get_html, set_html)

    def guardar(self):
        """Guarda el archivo, crea los directorios si no están."""
        destino = join(config.DIR_PREPROCESADO, self.ruta_relativa)
        try:
            os.makedirs(dirname(destino))
        except os.error:
            # ya estaba
            pass

        with open(destino, 'wb') as fh:
            fh.write(self._html)

    def __str__(self):
        return "<WikiArchivo: %s>" % self.url.encode("utf8")


class WikiSitio(object):
    def __init__(self, dir_raiz):
        self.origen = unicode(abspath(dir_raiz))
        self.resultados = {}
        self.preprocesadores = [proc(self) for proc in preprocesadores.TODOS]

        # let's see what was processed from before
        if os.path.exists(config.LOG_PREPROCESADO):
            fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
            fh.next()  # title
            procs = [p for p in self.preprocesadores]
            for linea in fh:
                partes = linea.split(config.SEPARADOR_COLUMNAS)
                arch = partes[0]
                dir3 = partes[1]
                d = {}
                self.resultados[arch] = d
                d["dir3"] = dir3
                for proc, ptje in zip(procs, map(int, partes[2:])):
                    d[proc] = ptje

        # vemos que habíamos descartado antes, y dejamos el archivo listo
        # para seguir escribiendo
        self.descartados_antes = set()
        nomarch = join(config.DIR_TEMP, "descartados.txt")
        if os.path.exists(nomarch):
            self.descartados_file = codecs.open(nomarch, 'r+', 'utf8')
            for linea in self.descartados_file:
                self.descartados_antes.add(linea.strip())
        else:
            self.descartados_file = codecs.open(nomarch, 'w', 'utf8')

    def procesar(self):
        resultados = self.resultados
        puntaje_extra = {}
        de_antes = 0

        # get the total of directories to parse
        total_dirs = sum(1 for _ in os.walk(self.origen))
        logger.info("Quantity of directories to process: %d", total_dirs)

        count = 0
        tl = utiles.TimingLogger(30, logger.debug)
        for cwd, directorios, archivos in os.walk(self.origen):
            partes_dir = cwd.split(os.path.sep)
            ult3dirs = join(*partes_dir[-3:])
            count += 1

            if len(ult3dirs) != 5:  # ej: u"M/a/n"
                # we're not in a leaf, we shouldn't have any files
                if archivos:
                    logger.warning("We have content in a non-leaf "
                                   "directory: %s", archivos)
                continue
            tl.log("Processing %s (%d/%d)", ult3dirs, count, total_dirs)

            for pag in archivos:
                if " " in pag:
                    logger.warning("Have names with spaces! %s %s",
                                   ult3dirs, pag)
                # vemos si lo teníamos de antes
                if pag in resultados:
                    de_antes += 1
                    continue
                if pag in self.descartados_antes:
                    continue

                wikiarchivo = WikiArchivo(cwd, ult3dirs, pag)
                resultados[pag] = {}
                resultados[pag]["dir3"] = ult3dirs

                for procesador in self.preprocesadores:
                    (puntaje, otras_pags) = procesador(wikiarchivo)

                    # agregamos el puntaje extra
                    for extra_pag, extra_ptje in otras_pags:
                        if extra_pag in resultados:
                            prev = resultados[extra_pag].get(procesador, 0)
                            resultados[extra_pag][procesador] = prev + extra_ptje
                        else:
                            ant = puntaje_extra.setdefault(extra_pag, {})
                            ant[procesador] = ant.get(procesador, 0) + extra_ptje

                    # None significa que el procesador lo marcó para omitir
                    if puntaje is None:
                        del resultados[pag]
                        self.descartados_file.write("%s\n" % pag)
                        break

                    # ponemos el puntaje
                    if puntaje != 0:
                        resultados[pag][procesador] = puntaje

                else:
                    # lo guardamos sólo si no fue descartado
                    wikiarchivo.guardar()

        for procesador in self.preprocesadores:
            procesador.close()
            logger.debug("Preprocessor %17s usage stats: %s", procesador.nombre, procesador.stats)

        # cargamos los redirects para tenerlos en cuenta
        redirects = {}
        sepcol = config.SEPARADOR_COLUMNAS
        with codecs.open(config.LOG_REDIRECTS, "r", "utf-8") as fh:
            for linea in fh:
                r_from, r_to = linea.strip().split(sepcol)
                redirects[r_from] = r_to

        # agregamos el puntaje extra sólo si ya teníamos las páginas con nos
        logger.debug("Distributing extra scope: %d", len(puntaje_extra))
        perdidos = []
        for (pag, puntajes) in puntaje_extra.items():
            # desreferenciamos el redirect, vaciando el diccionario para
            # evitar loops
            while pag in redirects:
                pag = redirects.pop(pag)

            # asignamos los puntajes para las páginas que están
            if pag in resultados:
                for (proc, ptje) in puntajes.items():
                    resultados[pag][proc] = resultados[pag].get(proc, 0) + ptje
            else:
                perdidos.append((pag, puntajes))
        if perdidos:
            logger.warning("Lost %d scores!", len(perdidos))
            fname = join(config.DIR_TEMP, 'perdidos.txt')
            with codecs.open(fname, 'w', 'utf8') as fh:
                for pag in perdidos:
                    fh.write(u"%s\n" % (pag,))

        return len(resultados) - de_antes, de_antes

    def guardar(self):
        log = abspath(config.LOG_PREPROCESADO)
        preprocs = self.preprocesadores
        sep_cols = unicode(config.SEPARADOR_COLUMNAS)
        plantilla = sep_cols.join([u'%s'] * (len(preprocs) + 2)) + "\n"

        # inicializamos el log
        salida = codecs.open(log, "w", "utf-8")
        columnas = [u'Página', u"Dir3"] + [p.nombre for p in preprocs]
        salida.write(plantilla % tuple(columnas))

        # Contenido:
        for pagina, valores in self.resultados.iteritems():
            #los rankings deben ser convertidos en str para evitar
            # literales como 123456L
            columnas = [pagina, valores["dir3"]]
            columnas += [valores.get(p, 0) for p in preprocs]
            salida.write(plantilla % tuple(columnas))

        logger.debug("Record written in %s", log)
        salida.close()


class PagesSelector(object):
    """Select the htmls that will be included in this version."""

    def __init__(self):
        self._calculated = False

        self._top_pages = None
        self._same_info_through_runs = None

    @property
    def top_pages(self):
        """The list of top pages."""
        if not self._calculated:
            raise ValueError("You need to first 'calculate' everything.")
        return self._top_pages

    @property
    def same_info_through_runs(self):
        """The top HTMLs for this run is the same of the previous one."""
        if not self._calculated:
            raise ValueError("You need to first 'calculate' everything.")
        return self._same_info_through_runs

    def calculate(self):
        """Calculate the HTMLs with more score and store both lists."""
        self._calculated = True

        # read the preprocessed file
        fh = codecs.open(config.LOG_PREPROCESADO, "r", "utf8")
        fh.next()  # title
        all_pages = []
        for linea in fh:
            partes = linea.split(config.SEPARADOR_COLUMNAS)
            arch = partes[0]
            dir3 = partes[1]
            puntaje = sum(map(int, partes[2:]))
            all_pages.append((dir3, arch, puntaje))

        # order by score, and get top N
        all_pages.sort(key=operator.itemgetter(2), reverse=True)
        page_limit = config.imageconf['page_limit']
        self._top_pages = all_pages[:page_limit]

        # get all items after N that still has the same score that last one
        last_score = self._top_pages[-1][2]
        for more_info in all_pages[page_limit:]:
            if more_info[2] == last_score:
                self._top_pages.append(more_info)

        separator = config.SEPARADOR_COLUMNAS
        if os.path.exists(config.PAG_ELEGIDAS):
            # previous run for this info! same content?
            with codecs.open(config.PAG_ELEGIDAS, "rt", "utf8") as fh:
                old_stuff = []
                for linea in fh:
                    dir3, arch, score = linea.strip().split(separator)
                    old_stuff.append((dir3, arch, int(score)))
                if sorted(old_stuff) == sorted(self._top_pages):
                    self._same_info_through_runs = True

        if not self._same_info_through_runs:
            # previous info not there, or different: write to disk
            with codecs.open(config.PAG_ELEGIDAS, "wt", "utf8") as fh:
                for dir3, arch, score in self._top_pages:
                    info = (dir3, arch, str(score))
                    fh.write(separator.join(info) + "\n")

pages_selector = PagesSelector()


def run(dir_raiz):
#    import cProfile
    wikisitio = WikiSitio(dir_raiz)
#    cProfile.runctx("wikisitio.procesar()", globals(), locals(), "/tmp/procesar.stat")
    cantnew, cantold = wikisitio.procesar()
    wikisitio.guardar()
    return cantnew, cantold

if __name__ == "__main__":
    run()