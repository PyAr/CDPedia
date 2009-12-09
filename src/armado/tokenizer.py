# -*- coding: utf8 -*-

"""
Biblioteca para extraer las propiedades indexables de un HTML

Se usa sólo desde cdpindex para crear el índice.
"""

import re
import unicodedata
import config
from itertools import ifilter

flags = re.UNICODE | re.DOTALL

substCREsCase = [
    (re.compile(ur"([a-z]+)([A-Z][a-z]+)",flags), "\\1 \\2"),        # fix para camelcase - así se indexa cada componente por separado
]
substCREs = [
    (re.compile(ur"&(.)(?:acute|tilde);?",flags), "\\1"),            # fix para el markup (entities a conservar)
    (re.compile(ur"&(?:\w+|#[0-9a-fA-F]+);?",flags), " "),           # fix para el markup (entities a tirar)
    (re.compile(ur"Ç",flags), "C"),                                  # acentuados
    (re.compile(ur"ñ",flags), "n"), 
    (re.compile(ur"[ÁÀÂÄÅÃ]".lower(),flags), "a"), 
    (re.compile(ur"[ÉÈÊË]".lower(),flags), "e"), 
    (re.compile(ur"[ÍÌÎÏ]".lower(),flags), "i"),
    (re.compile(ur"[ÓÒÔÖÕ]".lower(),flags), "o"), 
    (re.compile(ur"[ÚÙÛÜ]".lower(),flags), "u"), 
    (re.compile(ur"[®©!~'<>¿?°º]",flags), " "),
]

# este es la regex simpla para separar palabras a lo pavote
splitRE  = ur'(?:(?:\W|[_])+|(\d+)([khcnu]?(?:[mwgs]|ev|hz)[23]?)s?(?=\W)|(\d+)([khcmptg]b?)(?=\W)|(\d+)[x](\d+))'
splitCRE_simple = re.compile(splitRE,flags)

# std separa términos de interés, preserva números con su signo y cosas por el estilo
# OJO - el espacio al final del primer [] NO es un espacio común
splitRE  = ur'(?:\s|[&\|";\\?\]\[():\' ]|(?<=\D)[.,]|[-.,](?=\D)|[.]\Z|-(?=\s*(?:\D|$))|(?<!\d)\s*/\s*(?!\d)|(?<!/)\s(?!/))+'
splitCRE_std = re.compile(splitRE,flags)

# nsep separa números mejor para aplicar TFIDF en aglomeraciones de propiedades numéricas
splitRE_nsep = ur'(?:\s|[&\|";\\?\]\[():\' ]|(?<=\D)[.,]|[-.,](?=\D)|[.]\Z|-(?=\s*(?:\D|$))|(?<!\d)\s*/\s*(?!\d)|(?<!/)\s(?!/)|(?<=\d)\s*[xX]\s*(?=\d*(\Z|[\s&\|";\\?\]\[():\' ])))+'
splitCRE_nsep= re.compile(splitRE_nsep,flags)

#_PALABRAS = re.compile("\w+", re.UNICODE)

def _normaliza(txt):
    '''Recibe una frase y devuelve el texto ya normalizado.'''
    return unicodedata.normalize('NFKD', txt).encode('ASCII', 'replace')

def tokenize(text, 
        splitCRE=splitCRE_simple, 
        substCREs=substCREs, 
        substCREsCase=substCREsCase):
    #return _PALABRAS.findall(_normaliza(text))
    
    if not text:
        return []

    for re, val in substCREsCase:
        text = re.sub(val, text)

    text = text.lower()

    for re, val in substCREs:
        text = re.sub(val, text)
    
    text = _normaliza(text)
    
    return ifilter(bool,splitCRE.split(text))


