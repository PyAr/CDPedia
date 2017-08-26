#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uso: preprocesar.py

Aplica los procesadores definidos en preprocesadores a cada
una de las páginas, para producir la prioridad con la que página
será (o no) incluída en la compilación.

"""

from __future__ import with_statement, unicode_literals, print_function

import os
import codecs
import config
import logging
import operator
import sys
import time

from collections import Counter
from os.path import join, abspath, dirname

from src.armado import to3dirs
from src.preproceso import preprocesadores
from src import utiles

logger = logging.getLogger(__name__)

LOG_SCORES_ACCUM = os.path.join(config.DIR_TEMP, 'page_scores_accum.txt')
LOG_SCORES_FINAL = os.path.join(config.DIR_TEMP, 'page_scores_final.txt')


class WikiArchivo(object):
    def __init__(self, cwd, last3dirs, nombre_archivo):
        self.ruta_relativa = join(last3dirs, nombre_archivo)
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

    def __init__(self, root_dir):
        self.origen = unicode(abspath(root_dir))
        self.preprocesadores = [proc() for proc in preprocesadores.TODOS]
        self.prof_quant = Counter()
        self.prof_times = Counter()

    def process(self):
        """Process all pages under a root directory."""
        # let's see what was processed from before, and open the log file to keep adding
        if os.path.exists(config.LOG_PREPROCESADO):
            with codecs.open(config.LOG_PREPROCESADO, "rt", "utf8") as fh:
                processed_before_set = set(x.strip() for x in fh)
        else:
            processed_before_set = set()
        processed_before_log = codecs.open(config.LOG_PREPROCESADO, "at", "utf8")

        # get the total of directories to parse
        logger.info("Getting how many pages under root dir")
        total_pages = sum(len(filenames) for _, _, filenames in os.walk(self.origen))
        logger.info("Quantity of pages to process: %d", total_pages)

        # open the scores file to keep adding
        scores_log = codecs.open(LOG_SCORES_ACCUM, "at", "utf8")

        count_processed = count_new_ok = count_new_discarded = count_old_before = 0
        tl = utiles.TimingLogger(30, logger.debug)
        for cwd, _, filenames in os.walk(self.origen):
            parts_dir = cwd.split(os.path.sep)
            last3dirs = join(*parts_dir[-3:])

            if len(last3dirs) != 5:  # ej: u"M/a/n"
                # we're not in a leaf, we shouldn't have any files
                if filenames:
                    logger.warning("We have content in a non-leaf directory: %s %s",
                                   last3dirs, filenames)
                continue

            for page_path in filenames:
                count_processed += 1
                tl.log("Processing %s (%d/%d)", last3dirs, count_processed, total_pages)

                if " " in page_path:
                    logger.warning("Have names with spaces! %s %s", last3dirs, page_path)

                # check if the page was processed or discarded before
                if page_path in processed_before_set:
                    count_old_before += 1
                    continue

                wikipage = WikiArchivo(cwd, last3dirs, page_path)

                this_total_score = 0
                other_pages_scores = []
                for procesador in self.preprocesadores:
                    tini = time.time()
                    try:
                        (this_score, other_scores) = procesador(wikipage)
                    except:
                        logger.error("Processor %s crashed on page %r", procesador, page_path)
                        raise
                    self.prof_times[procesador] += time.time() - tini
                    self.prof_quant[procesador] += 1

                    # keep the score for other pages (check before to avoid a bogus function call)
                    if other_scores:
                        other_pages_scores.extend(other_scores)

                    if this_score is None:
                        # the processor indicated to discard this page
                        count_new_discarded += 1
                        break

                    # keep the score for this page
                    this_total_score += this_score

                else:
                    # all processors done, page not discarded
                    count_new_ok += 1
                    wikipage.guardar()

                    # save the real page score
                    scores_log.write("{}|R|{:d}\n".format(
                        to3dirs.to_pagina(page_path), this_total_score))

                    # save the extra pages score (that may exist or not in the dump)
                    for extra_page, extra_score in other_pages_scores:
                        scores_log.write("{}|E|{:d}\n".format(extra_page, extra_score))

                # with score or discarded, log it as processed
                processed_before_log.write(page_path + "\n")

        # all processing done for all the pages
        logger.info("Processed pages: %d new ok, %d discarded, %d already processed before",
                    count_new_ok, count_new_discarded, count_old_before)
        scores_log.close()
        processed_before_log.close()
        for procesador in self.preprocesadores:
            procesador.close()
            logger.debug("Preprocessor %17s usage stats: %s", procesador.nombre, procesador.stats)

    def commit(self):
        """Commit all the processing done, adjusting some logs."""
        colsep = config.SEPARADOR_COLUMNAS

        # load the score files and compress it
        all_scores = Counter()
        real_pages = set()
        with codecs.open(LOG_SCORES_ACCUM, "rt", "utf8") as fh:
            for line in fh:
                page, status, score = line.strip().split(colsep)
                all_scores[page] += int(score)
                if status == 'R':
                    real_pages.add(page)

        # load the redirects
        redirects = {}
        with codecs.open(config.LOG_REDIRECTS, "r", "utf-8") as fh:
            for linea in fh:
                r_from, r_to = linea.strip().split(colsep)
                redirects[r_from] = r_to

        # transfer score
        transferred_scores = Counter()
        for page, score in all_scores.items():
            if page not in redirects:
                transferred_scores[page] += score
                continue

            # dereference the redirect, avoiding a possible loop; note that intermediate
            # pages have not score (see processor)
            loop_guard = []
            while page in redirects:
                page = redirects[page]
                if page in loop_guard:
                    logger.warning("Redirect loop found: %s", loop_guard, page)
                    break
                loop_guard.append(page)

            # add the original score to the dereferenced page
            transferred_scores[page] += score

        # store the scores again, but only for the real pages (there is no point in storing
        # scores for pages that were not included in the dump)
        with codecs.open(LOG_SCORES_FINAL, "wt", "utf8") as fh:
            for page in real_pages:
                fh.write("{}|{:d}\n".format(page, transferred_scores[page]))


class PagesSelector(object):
    """Select the htmls that will be included in this version."""

    def __init__(self):
        self._calculated = False
        self._top_pages = None

        # used from outside to decided regenerate index, blocks, etc
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
        all_pages = []
        colsep = config.SEPARADOR_COLUMNAS
        with codecs.open(LOG_SCORES_FINAL, 'rt', encoding='utf8') as fh:
            for line in fh:
                page, score = line.strip().split(colsep)
                dir3, fname = to3dirs.get_path_file(page)
                all_pages.append((dir3, fname, page, int(score)))

        # order by score, and get top N
        all_pages.sort(key=operator.itemgetter(3), reverse=True)
        page_limit = config.imageconf['page_limit']
        self._top_pages = all_pages[:page_limit]

        # get all items after N that still has the same score that last one
        last_score = self._top_pages[-1][3]
        for more_info in all_pages[page_limit:]:
            if more_info[3] == last_score:
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
                for dir3, fname, page, score in self._top_pages:
                    info = (dir3, page, str(score))
                    fh.write(separator.join(info) + "\n")

pages_selector = PagesSelector()


def run(root_dir):
    if os.path.exists(LOG_SCORES_FINAL):
        logger.info("Skipping the whole processing stage as the final scores log was found.")
        return

    wikisitio = WikiSitio(root_dir)
    wikisitio.process()
    wikisitio.commit()


def profiled_run(root_dir):
    # import cProfile

    tini = time.time()
    wikisitio = WikiSitio(root_dir)

    # uncomment the following if you want to profile just ONE preprocessor (fix which one)
    wikisitio.preprocesadores = [preprocesadores.HTMLCleaner()]

    # select here to run the profiled process or not
    # cProfile.runctx("wikisitio.process()", globals(), locals(), "/tmp/procesar.stat")
    wikisitio.process()

    wikisitio.commit()
    tend = time.time()
    print("Whole process", tend - tini)
    print("In processors", sum(wikisitio.prof_times.values()))
    for proc in wikisitio.prof_times:
        quant = wikisitio.prof_quant[proc]
        total = wikisitio.prof_times[proc]
        print("         proc ", proc, quant, total, total / quant)
    print("Full stats (if profile run) saved in /tmp/procesar.stat")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: preprocesar.py root_dir")
        exit()
    if os.path.exists(config.LOG_PREPROCESADO):
        print("ERROR: The PREPROCESADO file is there, it will make some articles to be skipped:",
              config.LOG_PREPROCESADO)
        exit()

    # fix config for a needed variable
    config.langconf = dict(include=[])

    profiled_run(sys.argv[1])
