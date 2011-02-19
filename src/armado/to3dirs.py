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

    return os.path.join(*dirs)

def to_complete_path(pagina):
    return os.path.join(to_path(pagina), to_filename(pagina))

def to_filename(pagina):
    if ':' in pagina:
        namespace = pagina[:pagina.find(':')+1]
        pagina = pagina[pagina.find(':')+1:]
    else:
        namespace = ''
    return namespace + _escape_filename(pagina)

if __name__ == "__main__":
    assert os.path.join(u"*", NULL, NULL) == to_path(u"*/")
    assert os.path.join(u"a", u"b", u"c") == to_path(u"abcdefgh")
    assert os.path.join(u"á", NULL, NULL) == to_path(u"á")
    assert os.path.join(u"á", u"þ", NULL) == to_path(u"áþ")
    assert os.path.join(u"$", u"9", NULL) == to_path(u"$9.99")

    assert u"*"+ BARRA == to_filename(u"*/")
    assert u"Anexo:*"+ BARRA == to_filename(u"Anexo:*/")
    assert os.path.join(u"a", u"b", u"c") == to_path(u"Anexo:abcdefgh")

    assert os.path.join(u'a',u':',u'b') == to_path(u'Anexo:a:blanco')
    assert os.path.join(u'N',u'o',u'e') == to_path(u'Noestoy:Anexo:a:blanco')
