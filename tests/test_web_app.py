# -*- coding: utf8 -*-

# Copyright 2011-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/


import os
import tarfile
from unittest.mock import patch

from werkzeug.test import Client
from werkzeug.wrappers import Response

import config
from src.armado import cdpindex
from src.armado.sqlite_index import Indexentry
from src.web import web_app, utils

import pytest


@pytest.fixture
def create_app_client(mocker, tmp_path):
    """Helper to create tests app and client."""

    # fix config and write some setup files
    config.DIR_ASSETS = str(tmp_path)
    mocker.patch('config.LANGUAGE', 'es')
    mocker.patch('config.PORTAL_PAGE', 'Portal:Portal')
    mocker.patch('config.URL_WIKIPEDIA', 'http://es.wikipedia.org/')
    mocker.patch('config.PYTHON_DOCS_FILENAME', 'docs.tar.bz2')
    mocker.patch('src.armado.compresor.ArticleManager.archive_dir', str(tmp_path))
    mocker.patch('src.armado.compresor.ImageManager.archive_dir', str(tmp_path))
    mocker.patch.dict('os.environ', {'LANGUAGE': 'es'})
    with (tmp_path / 'numbloques.txt').open('wt') as fh:
        fh.write('42\n')
    with (tmp_path / 'language.txt').open('wt') as fh:
        fh.write('es\n')
    with tarfile.open(str(tmp_path / config.PYTHON_DOCS_FILENAME), 'w:bz2') as fh:
        fh.addfile(tarfile.TarInfo(name="testtuto"))
    inst_dir = tmp_path / 'institucional'
    inst_dir.mkdir()
    with (inst_dir / 'ayuda.html').open('wt') as fh:
        fh.write('lot of help\n')

    dynamic_assets = tmp_path / 'dynamic'
    dynamic_assets.mkdir()
    with (dynamic_assets / 'start_date.txt').open('wt') as fh:
        fh.write('20201122\n')

    # a bogus index with a couple of items (so it behaves properly for get_random and similar)
    mocker.patch('config.DIR_INDICE', str(tmp_path))
    entry1 = Indexentry(link='p/a/g/page1', title='Page1')
    entry2 = Indexentry(link='p/a/g/page2', title='Page2')
    fake_content = [(['key1'], 7, entry1),
                    (['key2'], 8, entry2)]
    cdpindex.Index.create(str(tmp_path), fake_content)

    app = web_app.create_app(watchdog=None, with_static=False)
    client = Client(app, Response)
    return lambda: (app, client)


def test_main_page_portal(create_app_client):
    app, client = create_app_client()

    def fake_get_item(name):
        assert name == "Portal:Portal"
        return "Fake article"

    app.art_mngr.get_item = fake_get_item
    response = client.get("/")
    assert response.status_code == 200
    assert b"Fake article" in response.data


def test_main_page_featured(create_app_client):
    app, client = create_app_client()
    with patch.object(app.featured_mngr, 'get_destacado', lambda: ('link', 'title', 'paragraphs')):
        response = client.get("/")
    assert "Artículo destacado".encode("utf-8") in response.data


def test_images_not_found(create_app_client):
    _, client = create_app_client()
    # Test images generated on the fly when the img is not found.
    response = client.get("/images/an/invalid/image/img.png?s=5-5")
    assert response.status_code == 200
    assert response.headers["Content-type"] == "image/svg+xml; charset=utf-8"

    response = client.get("/images/an/invalid/image/img.png")
    assert response.status_code == 500


def test_wiki_article_not_found(create_app_client):
    _, client = create_app_client()
    response = client.get("/wiki/this_article_does_not_exists")
    assert response.status_code == 404


def test_wiki_article_maradona(create_app_client):
    app, client = create_app_client()
    app = web_app.create_app(watchdog=None, with_static=False)
    app.art_mngr.get_item = lambda x: "Fake article <a>Yo soy el Diego</a>"
    client = Client(app, Response)
    response = client.get("/wiki/Diego_Armando_Maradona")
    assert response.status_code == 200
    assert b"Yo soy el Diego" in response.data


def test_wiki_article_with_special_chars(create_app_client):
    app, client = create_app_client()
    app = web_app.create_app(watchdog=None, with_static=False)
    html = "foo <a>bar</a> baz"
    app.art_mngr.get_item = lambda x: html
    client = Client(app, Response)
    response = client.get("/wiki/.foo/bar%baz")
    assert response.status_code == 200
    assert html.encode('utf-8') in response.data


def test_wiki_random_article(create_app_client):
    _, client = create_app_client()
    response = client.get("/al_azar")
    assert response.status_code == 302
    assert b"Redirecting..." in response.data
    assert response.location.startswith('http://localhost/wiki/')


def test_institucional(create_app_client):
    _, client = create_app_client()
    response = client.get("/institucional/ayuda.html")
    assert response.status_code == 200
    assert b"Ayuda" in response.data


def test_watchdog_off(create_app_client):
    app, client = create_app_client()
    app = web_app.create_app(watchdog=None, with_static=False)
    client = Client(app, Response)
    response = client.get("/")
    assert b"watchdog" not in response.data


def test_watchdog_on(create_app_client):
    app, client = create_app_client()
    app = web_app.create_app(watchdog=True, with_static=False)
    client = Client(app, Response)
    response = client.get("/")
    assert b"watchdog" in response.data


def test_index_ready(create_app_client):
    app, client = create_app_client()
    app = web_app.create_app(watchdog=None, with_static=False)
    client = Client(app, Response)

    class FakeIndex(object):
        def __init__(self):
            self.ready = False

        def is_ready(self):
            return self.ready

    app.index = FakeIndex()
    response = client.get("/search_index/ready")
    assert response.data == b"false"

    app.index.ready = True
    response = client.get("/search_index/ready")
    assert response.data == b"true"


def test_search_get(create_app_client):
    _, client = create_app_client()
    response = client.get("/search")
    assert response.status_code == 200


def test_search_post_url(create_app_client):
    _, client = create_app_client()
    response = client.post("/search")
    assert response.status_code == 302


def test_search_post(create_app_client):
    _, client = create_app_client()
    response = client.post("/search", data={"keywords": "a"})
    assert response.status_code == 302
    assert "/search/" in response.location
    response = client.post("/search", data={"keywords": "a"}, follow_redirects=True)
    assert response.status_code == 200


def test_search_term_url(create_app_client):
    _, client = create_app_client()
    words = ("foo", "bar")
    response = client.post("/search", data={"keywords": " ".join(words)})

    assert response.status_code == 302
    assert "/search/%s" % "+".join(words) in response.location

    response = client.post(
        "/search", data={"keywords": " ".join(words)}, follow_redirects=True)
    assert response.status_code == 200


def test_search_term_with_slash(create_app_client):
    _, client = create_app_client()
    data = {"keywords": "foo/bar"}
    response = client.post("/search", data=data, follow_redirects=True)
    assert response.status_code == 200


def test_on_tutorial(create_app_client):
    _, client = create_app_client()
    response = client.get("/tutorial")
    assert response.status_code == 200


def test_on_favicon(create_app_client):
    # fake a favicon (note that DIR_ASSETS is a temp dir created above)
    os.makedirs(os.path.join(config.DIR_ASSETS, 'static', 'misc'))
    _path = os.path.join(config.DIR_ASSETS, 'static', 'misc', 'favicon.ico')
    test_content = b"this is content to for the test"
    with open(_path, "wb") as fh:
        fh.write(test_content)

    _, client = create_app_client()
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert test_content in response.data


def test_get_origin_link(create_app_client):
    assert utils.get_orig_link('Python').endswith("/wiki/Python")
    assert utils.get_orig_link('"Love_and_Theft"').endswith("/wiki/%22Love_and_Theft%22")
