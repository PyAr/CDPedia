"""The scrapper for the portals."""

from __future__ import print_function

import bs4

PARSED_TITLE_STYLE = (
    "text-align: left; font-family: sans-serif; font-size:130%; "
    "border-bottom: solid 2px #7D80B3; margin-bottom:5px;")

G_MAIN_STRUCT = b"""
<div style="{style}">
{header}
<br/>
<div style="font-size: 80%">
    <ul>
{items}
    </ul>
</div>
</div>
"""

G_MAIN_STYLE_FIRST = b"padding-bottom: 0.5em; padding-top: 0.5em;"
G_MAIN_STYLE_REST = (
    b"border-top: 1px dotted rgb(192, 136, 254); padding-bottom: 0.5em; padding-top: 0.5em;")

G_TITLE = b"""\
    <div class="floatright">
        <img width="30" height="30" src="{image_src}" />
    </div>
    {titles}
"""

G_TIT_FMT_LINKED = b'<b><a href="{url}">{text}</a></b>'
G_TIT_FMT_NOLINK = b'<b>{text}</b>'
G_TIT_SEP = b', '

G_ITEM_FMT = b'<a href="{url}">{text}</a>'
G_ITEM_SEP = b' - '
G_ITEM_BULL = b'        <li>{item}</li>'


def _build_titles(titles):
    """Build the titles string."""
    titles_str = []
    for text, url in titles:
        if url is None:
            titles_str.append(G_TIT_FMT_NOLINK.format(text=text.encode('utf8')))
        else:
            titles_str.append(G_TIT_FMT_LINKED.format(text=text.encode('utf8'), url=url))
    return G_TIT_SEP.join(titles_str)


def generate(items):
    """Generate the 'portals' html to be included in the releases."""
    result = []
    for item in items:
        icon, titles, sub_simples, sub_complexes = item

        # the style
        if not result:
            style = G_MAIN_STYLE_FIRST
        else:
            style = G_MAIN_STYLE_REST

        # the header
        header = G_TITLE.format(image_src=icon, titles=_build_titles(titles))

        # the items
        items = []
        if sub_simples:
            items.append(G_ITEM_SEP.join(G_ITEM_FMT.format(text=text.encode('utf8'), url=url)
                                         for text, url in sub_simples))
        for c_titles, c_items in sub_complexes:
            fmt_titles = _build_titles(c_titles)
            if c_items:
                fmt_items = G_ITEM_SEP.join(G_ITEM_FMT.format(text=text.encode('utf8'), url=url)
                                            for text, url in c_items)
                items.append(": ".join((fmt_titles, fmt_items)))
            else:
                items.append(fmt_titles)

        items_str = "\n".join(G_ITEM_BULL.format(item=item) for item in items)
        result.append(G_MAIN_STRUCT.format(style=style, header=header, items=items_str))
    return "".join(result)


def _es_parser(html):
    """The parser for Spanish portals."""
    soup = bs4.BeautifulSoup(html, 'lxml')
    result = []

    def _get_chunks():
        content = soup.find('div', {'id': 'bodyContent'})
        table = content.find('table')
        chunk = []
        for item in table.find_all():
            if item.name == 'img' and item.get('alt', '').startswith('P '):
                # if have previous chunk, return it
                if chunk:
                    yield chunk
                chunk = [item]
                continue

            if item.name == 'div' and item.get('style') == PARSED_TITLE_STYLE:
                chunk.append(item)
                continue

            if item.name == 'p':
                chunk.append(item)
                continue
        yield chunk

    useful = False
    for chunk in _get_chunks():
        image_node = chunk[0]
        title_node = chunk[1]
        items_node = chunk[2:]
        if not useful:
            if title_node.text == "Wikipedia":
                useful = True
            continue

        # the image
        icon = image_node['src']

        # the titles
        _as = title_node.find_all('a')
        if not _as:
            titles = [(title_node.text, None)]
        else:
            titles = [(_a.text, _a['href']) for _a in _as]

        # the items, with sub divisions or not
        if any(x.name == 'div' for x in items_node):
            sub_simples = []
            if items_node[0].name != 'div':
                first = items_node.pop(0)
                sub_simples.extend((n.text, n['href']) for n in first.find_all())
            assert items_node[0].name == 'div'
            title = None
            childs = None
            sub_complexes = []
            for item in items_node:
                if item.name == 'div':
                    if title is not None:
                        sub_complexes.append((title, childs))
                    _a = item.find('a')
                    title = [(_a.text, _a['href'])]
                    childs = []

                if item.name == 'p':
                    childs.extend((n.text.strip(':'), n.next['href']) for n in item.find_all('b'))
            sub_complexes.append((title, childs))

        else:
            sub_simples = []
            sub_complexes = []
            for item in items_node:
                # get parts ignoring br's
                parts = [part for part in item.find_all() if part.name != 'br']
                if not parts:
                    continue

                if parts[0].name == 'b':
                    # first item in bold, means a grouped sector of links
                    if parts[0].find('a'):
                        # the title of the sector is also a link
                        q_titles = len(parts[0].find_all())
                        sub_tit = []
                        for n in parts[1:1 + q_titles]:
                            if isinstance(n, basestring):
                                sub_tit.append((n, None))
                            else:
                                sub_tit.append((n.text, n['href']))
                    else:
                        # the title of the sector is not a link
                        sub_tit = [(parts[0].text.strip(":"), None)]
                        q_titles = 0
                    sub_itm = [(n.text, n['href']) for n in parts[q_titles + 1:]]
                    sub_complexes.append((sub_tit, sub_itm))
                else:
                    # simple links
                    sub_simples = [(n.text, n['href']) for n in parts]

        result.append((icon, titles, sub_simples, sub_complexes))

    return result


def chunkizer(items, cutter):
    """Separate any list of items in chunks."""
    useful = []
    for item in items:
        if cutter(item):
            yield useful
            useful = []
        useful.append(item)
    yield useful


def _pt_parser(html):
    """The parser for Portuguese portals."""
    soup = bs4.BeautifulSoup(html, 'lxml')
    result = []

    def _get_chunks():
        content = soup.find('div', {'id': 'bodyContent'})
        table = content.find('table')
        chunk = None
        for item in table.find_all():
            if item.name == 'h2':
                # if have previous chunk, return it
                if chunk:
                    yield chunk
                chunk = [item]
                continue

            if chunk is None:
                continue

            if item.name in ('h3', 'p'):
                chunk.append(item)
                continue

            if item.name == 'li':
                chunk.append(item)
                continue
        yield chunk

    for chunk in _get_chunks():
        # image and titles
        node = chunk[0]
        icon = node.find('img')['src']
        titles = [(_a.text, _a['href'])
                  for _a in node.find_all('a') if _a.get('class') != ['image']]

        # the items, first the simple ones from the first sub chunk
        sub_chunks = chunkizer(chunk[1:], lambda n: n.name != 'li')
        sub_simples = []
        for item in sub_chunks.next():
            for _a in item.find_all('a'):
                k = (_a.text, _a['href'])
                if k not in sub_simples:
                    sub_simples.append(k)

        # the rest are more complex
        sub_complexes = []
        for subchunk in sub_chunks:
            tit_node = subchunk[0]
            _a_tit = tit_node.find('a', class_=None)
            if _a_tit is None:
                if not tit_node.text:
                    continue
                sub_tit = [(tit_node.text, None)]
            else:
                sub_tit = [(_a_tit.text, _a_tit['href'])]
            sub_itm = []
            for it in subchunk[1:]:
                _a = it.find('a')
                sub_itm.append((_a.text, _a['href']))
            sub_complexes.append((sub_tit, sub_itm))
        result.append((icon, titles, sub_simples, sub_complexes))

    return result


_parsers = {
    'es': _es_parser,
    'pt': _pt_parser,
}


def parse(language, html):
    """Generic entry point for all parsers."""
    p = _parsers[language]
    return p(html)


if __name__ == '__main__':
    # code for manual testing purposes
    import urllib2
    import sys
    if len(sys.argv) != 3:
        print("To test: portals.py lang url_or_filepath")
        exit()
    lang = sys.argv[1]
    src = sys.argv[2]
    if src.startswith("http"):
        u = urllib2.urlopen(src)
        html_src = u.read()
    else:
        with open(src, 'rb') as fh:
            html_src = fh.read()

    items = parse(lang, html_src)
    print(generate(items))
