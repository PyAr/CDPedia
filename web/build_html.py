#!/usr/bin/env fades

import datetime
import pathlib
from collections import namedtuple
from operator import attrgetter

import humanize  # fades >= 3.7.1
import yaml  # fades
from babel.dates import format_date  # fades
from jinja2 import Template  # fades

TEMPLATES_DIR = pathlib.Path('templates')
IMAGES_DIR = pathlib.Path('images')
RESULTS_DIR = pathlib.Path('.')

BASE_URL = "http://cdpedia.python.org.ar"

ImageInfo = namedtuple('ImageInfo', "format_id size md5 sha1 torrent")
CurrentInfo = namedtuple('CurrentInfo', "lang version date formats")


def get_files_info(basedir):
    """Get information from the files in the directory."""
    # process the files to group per format, and validate all have same version and date
    lang = version = image_date = None
    by_format = {}
    for fpath in basedir.iterdir():
        prefix, this_lang, this_version, this_date, rest = fpath.name.split('-')
        assert prefix == 'cdpedia'
        if lang is None:
            lang = this_lang
        else:
            assert lang == this_lang
        if version is None:
            version = this_version
        else:
            assert version == this_version
        if image_date is None:
            image_date = this_date
        else:
            assert image_date == this_date

        image_format, *_, file_type = rest.split('.')
        if file_type == 'size':
            key = 'size'
            value = int(fpath.read_text())
        else:
            key = file_type
            value = str(fpath)
        by_format.setdefault(image_format, {})[key] = value

    # ensure all files found for each format and convert to a proper Image Info
    all_formats = []
    for image_format, info in by_format.items():
        if set(info) != {'md5', 'sha1', 'size', 'torrent'}:
            raise ValueError(f"Not all files found for format {image_format!r}, just: {set(info)}")
        info['format_id'] = image_format
        all_formats.append(ImageInfo(**info))

    return CurrentInfo(version=version, date=image_date, lang=lang, formats=all_formats)


def main():
    """Main entry point."""
    # load configs for produced images information and which language templates to use
    with open("../imagtypes.yaml", "rt", encoding="utf8") as fh:
        images_config = yaml.safe_load(fh)
    with open("../languages.yaml", "rt", encoding="utf8") as fh:
        langs_config = yaml.safe_load(fh)

    # check the available images
    images_info = []
    for available_lang in IMAGES_DIR.iterdir():
        current = available_lang / 'current'
        if not current.exists():
            raise ValueError("Cannot find current directory: {!r}".format(current))
        image_date = current.resolve().name
        print(f"Found current info for lang {available_lang.name!r}: {image_date}")

        info = get_files_info(current)
        assert info.lang == available_lang.name
        assert info.date == image_date
        images_info.append(info)

    # discover which templates are available
    templates_config_file = TEMPLATES_DIR / 'templates.yaml'
    templates_config = yaml.safe_load(templates_config_file.read_text())

    # generate the HTMLs
    for template_info in templates_config:
        for image_info in images_info:
            template_file = TEMPLATES_DIR / template_info['filename']
            template = Template(template_file.read_text())

            # cross links between all page languages for this CDPedia language
            all_pages_info = []
            for tinfo in templates_config:
                index_name = "index.{}.{}.html".format(tinfo['lang_id'], image_info.lang)
                all_pages_info.append((index_name, tinfo['lang_name']))

            # cross links between all CDPedia languages for this page language
            all_cdpedias_info = []
            for iinfo in images_info:
                index_name = "index.{}.{}.html".format(template_info['lang_id'], iinfo.lang)
                lang_name = langs_config[iinfo.lang]['language_name'][template_info['lang_id']]
                all_cdpedias_info.append((index_name, lang_name))

            # info for all images for the current CDPedia language
            all_produced_formats_info = []
            for format_info in sorted(image_info.formats, key=attrgetter('size')):
                image_config = images_config[image_info.lang][format_info.format_id]
                included_images_ratio = sum(image_config['image_reduction'][:-1])

                included_pages_quant = image_config['page_limit']
                if included_pages_quant is not None:
                    included_pages_quant = humanize.intcomma(included_pages_quant)

                info = {
                    'format': image_config['name'],
                    'size': humanize.naturalsize(format_info.size),
                    'pages': included_pages_quant,
                    'included_images_ratio': included_images_ratio,
                    'md5': format_info.md5,
                    'sha1': format_info.sha1,
                    'torrent': format_info.torrent,
                }
                all_produced_formats_info.append(info)

            image_date = datetime.datetime.strptime(image_info.date, "%Y%m%d")
            image_date_str = format_date(
                image_date, format='long', locale=template_info['lang_id'])
            context = {
                'version': image_info.version,
                'image_date': image_date_str,
                'pages_info': all_pages_info,
                'cdpedias_info': all_cdpedias_info,
                'all_images_url': "{}/images/{}/current/".format(BASE_URL, image_info.lang),
                'produced_formats_info': all_produced_formats_info,
            }

            rendered = template.render(context)
            index_name = "index.{}.{}.html".format(template_info['lang_id'], image_info.lang)
            index_file = RESULTS_DIR / index_name
            index_file.write_text(rendered)


main()
