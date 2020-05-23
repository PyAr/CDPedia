import os
from jinja2 import Template

templates = 'templates'

for lang_template in os.listdir(templates):

    language = lang_template.split('.')[1]

    with open(os.path.join(templates, lang_template), 'rt', encoding='utf8') as fh:
        template = Template(fh.read())

    if language == 'es':
        rendered = template.render(version='0.8.4', month_year='Junio 2017')
    elif language == 'en':
        rendered = template.render(version='0.8.4', month_year='June 2017')

    index_name = f'index.{language}.html'

    with open(index_name, 'wt', encoding='utf8') as fh:
        fh.write(rendered)
