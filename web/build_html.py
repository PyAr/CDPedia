#!/usr/bin/fades

import yaml  # fades
from jinja2 import Template  # fades

with open('index_template.es.html', 'rt', encoding='utf8') as fh:
    template = Template(fh.read())

variables_values = yaml.safe_load(open('./values_es.yaml'))

rendered = template.render(variables_values)

with open("index.es.html", "wt", encoding="utf8") as fh:
    fh.write(rendered)
