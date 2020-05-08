#!/usr/bin/fades

import yaml  # fades
from jinja2 import Template  # fades

with open('index.html', 'rt', encoding='utf8') as fh:
    template = Template(fh.read())

variables_values = yaml.full_load(open('./variables_values.yaml'))

rendered = template.render(variables_values)

with open("web.html", "wt", encoding="utf8") as fh:
    fh.write(rendered)
