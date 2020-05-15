#!/usr/bin/fades

import yaml  # fades
from jinja2 import Template  # fades

with open('index_template.es.html', 'rt', encoding='utf8') as fh:
    template = Template(fh.read())

rendered = template.render(version='0.8.4', month_year='Junio 2017')

with open("index.es.html", "wt", encoding="utf8") as fh:
    fh.write(rendered)
