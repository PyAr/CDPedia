# -*- coding: utf-8 -*-

import os

NULL = u"_"
BARRA = u"SLASH"

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

to_filename = _escape_filename


if __name__ == "__main__":
    assert os.path.join(u"*", NULL, NULL) == to_path(u"*/")
    assert os.path.join(u"a", u"b", u"c") == to_path(u"abcdefgh")
    assert os.path.join(u"á", NULL, NULL) == to_path(u"á")
    assert os.path.join(u"á", u"þ", NULL) == to_path(u"áþ")
    assert os.path.join(u"$", u"9", NULL) == to_path(u"$9.99")

    assert u"*"+ BARRA == to_filename(u"*/")

