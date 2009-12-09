# -*- coding: utf8 -*-

"""
Biblioteca para extraer el lexema básico de un token (palabra, cadena indexable)

Se usa sólo desde cdpindex para crear el índice.
"""

import re
import unicodedata
import config

flags = re.UNICODE

phonoCREs =[ (re.compile(u"[ÇSZ]|C(?=[EI])",flags), "S"), # Ssss
             (re.compile(u"C(?=[AOU])",flags),      "K"), # K
             (re.compile(u"[BV]",flags),            "B"), # B
            ]

# Setmming super básico
stemCREs = [ 
             # sufijos complejos primero
             # (re.compile(ur'(\w{4}\w*)(?:mente|miento|zacion|cion|p?tion|idad(?:es)?|cias?|bles?|ancia|dor(?:[ea]s)?)\Z',flags) , ur'\1'),
             #
             # ^ aunque reducen bastante la cantidad de términos, son términos que es interesante indexar y discernir:
             #   minimiza != minimización

             # sufijos complejos primero - conjugaciones
             (re.compile(ur'(\w{2}\w*a)ndo(?:l[oae]|se)?\Z',flags) , ur'\1'),     # andolo/a/se (la o/a se omite porque la regla de plural la quita)
             (re.compile(ur'(\w{2}\w*i)endo(?:l[oae]|se)?\Z',flags) , ur'\1'),    # ^ similar
             (re.compile(ur'(\w{2}\w*i)(?:ais|an)?\Z',flags) , ur'\1'),           # ^ similar
             (re.compile(ur'(\w{3}\w*[ia])(?:ste(?:is)?|se)?\Z',flags) , ur'\1'), # ^ similar

             # conjugaciones
             (re.compile(ur'(\w{2}\w*[aeioun]gue)n\Z',flags) , ur'\1'),  # (amorti|averi|apaci)-guen -> amorti-gue
             
             (re.compile(ur'(\w{2}\w*(?:[lytz]|[cs]i?|cu|tr|on))[a][ndb]\Z',flags) , ur'\1'),  # acuchill(aba/an/ad)
             (re.compile(ur'(\w{3}\w*er)ia[ns]?\Z',flags) , ur'\1'),  # er-ian/s (abastecer(ia(n/s))
             
             (re.compile(ur'(\w{2}\w*?aba)(?:ba)?[nsd]?\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{3}\w*(?:[^aeiou][aei]))r\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{2}\w*i)er[oa]n(?:se)?\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{2}\w*[ae])r(?:[oae]n)?(?:se)?\Z',flags) , ur'\1'), # verb(ran(se)) - paren(se) - esperen(se)
             (re.compile(ur'(\w{2}\w*ab)[aeo]\Z',flags) , ur'\1'),  # aba / abo
             (re.compile(ur'(\w{2}\w*on)[ae]n\Z',flags) , ur'\1'),  # abandon(en), perdon(en), ...
             
             # plurales, géneros
             (re.compile(ur'(\w{3}\w*(?:os|iv))[oa]?\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{3}\w*[eilrnmcjpdt])[aoe]s?\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{3}\w*[ao])s\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{3}\w*[lrnmcjpdt][e])s\Z',flags) , ur'\1'),
             (re.compile(ur'(\w{3}\w*[ek])s\Z',flags) , ur'\1'),
             
             # inglés - hay términos en inglés en el corpus - muchos
             (re.compile(ur'(\w{2}\w*(?:on|ic))al(?:ly)?\Z',flags) , ur'\1'),  # addition(al(ly)), domestic(al(ly)), ...
             (re.compile(ur'(\w{3}\w*(?:on|ic|an|ent))s\Z',flags) , ur'\1'),  # plurales: -ons, -ics, -ans
             (re.compile(ur'(\w{2}\w*n)ning\Z',flags) , ur'\1'),  # banning, canning, prunning, -nning
             (re.compile(ur'(\w{2}\w*)ing\Z',flags) , ur'\1'),  # -ing
             (re.compile(ur'(\w{3}\w*[aeiou]n)ian\Z',flags) , ur'\1'),  # -ian (bartonian, bretonian,  -nian)
             
             # ceros a la izq
             (re.compile(ur'0+([1-9]\d*)\Z',flags) , ur'\1'),
             
             # eliminar:
             (re.compile(ur'\A(?:0x)?([0-9a-f]{2})[0-9a-f]+\Z',flags) , ur'\1'),     #  <- numeros hexadecimales (de más de 2 dígitos - tomar 2 primeros)
             (re.compile(ur'\A(?:0x)?([0-9a-f]{0,2})\Z',flags) , ur'\1'),            #  <- numeros hexadecimales (de menos de 2 dígitos - eliminar prefijo 0x)
             (re.compile(ur'\A(\d{4})\d+',flags) , ur'\1'),                          #  <- numeros con más de 4 dígitos (tomar 4 primeros)
            ]

def stemmize(text):
    for (re, val) in stemCREs:
        text = re.sub(val, text)
    return text

def phonetize(text):
    for (re, val) in phonoCREs:
        text = re.sub(val, text)
    return text

def _normaliza(txt):
    '''Recibe una frase y devuelve el texto ya normalizado.'''
    return unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore')

def getLexem(tok,
        stemming=config.ENABLE_INDEX_STEMMING,
        phonetics=config.ENABLE_INDEX_PHONETIZATION,
        cache={}):
    """
    Toma un token (posiblemente unicode) y devuelve un lexema apropiado (cadena, posiblemente unicode).
    """
    
    # No queremos tokens con más de 20 letras
    # (para los que existan, las 20 primeras 
    #  deberían ser suficientemente filtrantes)
    tok = tok[:20]
    
    if tok in cache:
        return cache[tok]
    otok = tok
    if stemming:
        while True:
            ntok = stemmize(tok)
            if ntok == tok:
                break
            tok = ntok
    if phonetics:
        tok = phonetize(tok)
    if isinstance(tok,unicode):
        tok = _normaliza(tok)
    cache[otok] = tok
    return tok

