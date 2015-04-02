# -*- coding: utf-8 -*-

import os

NULL = u"_"
BARRA = u"SLASH"

NAMESPACES = [u'Portal_Discusión', u'Wikiproyecto', u'Categoría_Discusión',
              u'Imagen',  u'Usuario', u'Plantilla_Discusión', u'Categoría',
              u'Wikipedia_Discusión', u'Wikipedia',  u'Anexo', u'Portal',
              u'Usuario_Discusión', u'Anexo_Discusión',  u'Plantilla', u'Ayuda',
              u'Discusión', u'Wikiproyecto_Discusión']

def _escape_dir(s):
    return s.replace(u"/", NULL).replace(u".", NULL)

def _escape_filename(s):
    return s.replace(u"/", BARRA)

def to_pagina(filename):
    """
    s == to_pagina(_escape_filename(s))
    """
    return filename.replace(BARRA, u"/")

def to_path(pagina):
    """
    Pagina tiene que ser unicode.
    """
    if not pagina:
        raise ValueError

    if ':' in pagina:
        namespace, posible_pagina = pagina.split(':',1)
        if namespace in NAMESPACES:
            pagina = posible_pagina

    pagina = _escape_dir(pagina)
    dirs = []
    if len(pagina) == 1:
        dirs = [pagina, NULL, NULL]
    elif len(pagina) == 2:
        dirs = [pagina[0], pagina[1], NULL]
    else:
        dirs = list(pagina[:3])

    #FIXME: Si se quiere generar en Windows se debe cambiar '/' por '\'
    #       No se puede usar os.path.join porque al usarse cdpedia solo pueede
    #       ejecutarse en la plataforma que fue generado el iso
    return '/'.join(dirs)

def to_complete_path(pagina):
    #FIXME: Si se quiere generar en Windows se debe cambiar '/' por '\'
    return '/'.join((to_path(pagina), to_filename(pagina)))

def from_path(path):
    """ Quita los 3 dirs del path """
    path = to_pagina(path)
    return path[6:]


to_filename = _escape_filename
