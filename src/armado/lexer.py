# -*- coding: utf8 -*-

"""
Biblioteca para extraer la lista de lexemas de un texto (palabras, cadenas indexables)
"""

from .tokenizer import tokenize
from .stemmer import getLexem

import codecs
import config

def _texto_a_lexemas(txt,stop):
    for lex in filter(bool,map(getLexem, tokenize(txt))):
        if lex not in stop:
            yield lex

try:
    STOPWORDS = codecs.open(config.TEXT_STOPWORDS_FILE, "r", "utf8").read()
except IOError,e:
    print "WARNING: no se puede leer el archivo de stopwords", e
    STOPWORDS = u""

try:
    STOPWORDS_TITLE = codecs.open(config.TITLE_STOPWORDS_FILE, "r", "utf8").read()
except IOError,e:
    print "WARNING: no se puede leer el archivo de stopwords", e
    STOPWORDS_TITLE = u""

STOPWORDS = _texto_a_lexemas(STOPWORDS, set())
STOPWORDS_TITLE = _texto_a_lexemas(STOPWORDS_TITLE, set())

def texto_a_lexemas(txt,stop=STOPWORDS):
    return _texto_a_lexemas(txt,stop)


