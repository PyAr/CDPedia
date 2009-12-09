# -*- coding: utf8 -*-

"""
Biblioteca para extraer las propiedades indexables de un HTML

Se usa sólo desde cdpindex para crear el índice.
"""

import re
import src.preproceso.preprocesadores as preprocesadores
import types


# Buscamos todo hasta el último guión no inclusive, porque los
# títulos son como "Zaraza - Wikipedia, la enciclopedia libre"
_SACATIT = re.compile(".*?<title>([^<]*)\s+-", re.S)

flags = re.UNICODE | re.DOTALL | re.I
_BODY_SUBST = [
    (re.compile(ur"<script\s*[^>]*?/?>.*?</script>",flags), " "),    # scripts
    (re.compile(ur"<a\s+[^>]*?>\s*http://[^ ]*\s*</a>",flags), " "), # links con una url como texto
    (re.compile(ur"<a\s+[^>]*?>\s*Usuario:[^<]*</a>",flags), " "),   # links a usuarios
    (re.compile(ur"<tr\s+[^>]*?display:none[^>]*?>.*?</tr>",flags), " "), # <tr>s invisibles
                                                                     # ^ la wiki genera mucho HTML automático, y hay muchos
                                                                     #   <tr> invisibles con basura dentro.
    (re.compile(ur"<!--[^->]*?-->",flags), " "),                     # comentarios
    (re.compile(ur"</?[a-zA-Z0-9]+\s*[^>]*?/?>",flags), " "),        # tags
    
    (re.compile(ur"(https?|ftp)://\w+[^][ ]*",flags), " "),          # urls planas
]
del flags

def _getHTMLTitle(html):
    # Todavia no soportamos redirect, asi que todos los archivos son
    # válidos y debería tener TITLE en ellos
    m = _SACATIT.match(html)
    if m:
        tit = m.groups()[0]
    else:
        tit = u"<sin título>"
    return tit

class WikiMockup:
    def __init__(self, html):
        self.url = 'a.html'
        self.html = html

def _getHTMLText(html, extractor = preprocesadores.ExtraerContenido(None)):
    # Preparar un mockup de wikiarchivo
    wikiarchivo = WikiMockup(html)
    
    # llamar al extractor para que nos extraiga el contenido
    # ojo: podría tirar ValueError si no encuentra los marcadores
    #   apropiados, usaremos otro método en ese caso
    try:
        extractor(wikiarchivo)
    except ValueError:
        # el método más sofisticado del universo: pass
        pass
    
    return wikiarchivo.html

def _html2text(html):
    html = html.lower()

    for re, val in _BODY_SUBST:
        html = re.sub(val, html)
    
    return html

def propertiesFromHTML(html):
    """
    Toma un html (unicode), devuelve un diccionario de propiedades, 
    donde las claves son el nombre de la propiedad
    y los valores son el valor de la propiedad.
    
    Devuelve siempre un diccionario con las mismas claves.
    
    NOTA: Por ahora, las propiedades aceptadas (o tenidas en cuenta) son 'title' y 'text',
    pero nada impediría en un futuro indexar otras propiedades.
    """
    return {
        'title' : _getHTMLTitle(html),
        'text' : _html2text(_getHTMLText(html)),
    }

