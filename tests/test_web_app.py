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

import unittest

from src import third_party  # NOQA: Need this to import werkzeug
from src.web import web_app, utils

from werkzeug.test import Client
from werkzeug.wrappers import Response


class WebAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = web_app.create_app(watchdog=None, with_static=False)
        self.client = Client(self.app, Response)

    def tearDown(self):
        pass

    def test_main_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Bienvenido" in response.data)

    def test_main_page_destacado(self):
        response = self.client.get("/")
        if len(self.app.destacados_mngr.destacados) > 0:
            self.assertTrue(u"Artículo destacado".encode("utf-8") in response.data)

    def test_main_page_portales(self):
        response = self.client.get("/")
        self.assertTrue(u"Química".encode("utf-8") in response.data)
        self.assertTrue(u"Geografía".encode("utf-8") in response.data)

    def test_images_not_found(self):
        # Test images generated on the fly when the img is not found.
        response = self.client.get("/images/an/invalid/image/img.png?s=5-5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-type"], "img/bmp")

        response = self.client.get("/images/an/invalid/image/img.png")
        self.assertEqual(response.status_code, 500)

    def test_wiki_article_not_found(self):
        response = self.client.get("/wiki/this_article_does_not_exists")
        self.assertEqual(response.status_code, 404)

    def test_wiki_article_maradona(self):
        app = web_app.create_app(watchdog=None, with_static=False)
        app.art_mngr.get_item = lambda x: "Fake article <a>Yo soy el Diego</a>"
        client = Client(app, Response)
        response = client.get("/wiki/Diego_Armando_Maradona")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Yo soy el Diego" in response.data)

    def test_wiki_random_article(self):
        response = self.client.get("/al_azar")
        self.assertEqual(response.status_code, 302)
        self.assertTrue("Redirecting..." in response.data)

        response = self.client.get("/al_azar", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("De Wikipedia, la enciclopedia libre" in response.data)

    def test_institucional(self):
        response = self.client.get("/institucional/ayuda.html")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Ayuda" in response.data)

    def test_watchdog_off(self):
        app = web_app.create_app(watchdog=None, with_static=False)
        client = Client(app, Response)
        response = client.get("/")
        self.assertTrue("watchdog" not in response.data)

    def test_watchdog_on(self):
        app = web_app.create_app(watchdog=True, with_static=False)
        client = Client(app, Response)
        response = client.get("/")
        self.assertTrue("watchdog" in response.data)

    def test_index_ready(self):
        app = web_app.create_app(watchdog=None, with_static=False)
        client = Client(app, Response)

        class FakeIndex(object):
            def __init__(self):
                self.ready = False

            def is_ready(self):
                return self.ready

        app.index = FakeIndex()
        response = client.get("/search_index/ready")
        self.assertEqual(response.data, "false")

        app.index.ready = True
        response = client.get("/search_index/ready")
        self.assertEqual(response.data, "true")

    def test_search_get(self):
        response = self.client.get("/search")
        self.assertEqual(response.status_code, 200)

    def test_search_post_url(self):
        response = self.client.post("/search")
        self.assertEqual(response.status_code, 302)

    def test_search_post(self):
        response = self.client.post("/search", data={"keywords": "a"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/search/" in response.location)
        response = self.client.post("/search", data={"keywords": "a"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_search_term_url(self):
        words = (u"foo", u"bar")
        response = self.client.post("/search", data={"keywords": u" ".join(words)})
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/search/%s" % "+".join(words) in response.location)

        response = self.client.post(
            "/search", data={"keywords": u" ".join(words)}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_on_tutorial(self):
        response = self.client.get("/tutorial")
        self.assertEqual(response.status_code, 200)

def test_get_origin_link():
    assert utils.get_orig_link(u'Python').endswith(u"/wiki/Python")
    assert utils.get_orig_link(u'"Love_and_Theft"').endswith(u"/wiki/%22Love_and_Theft%22")


if __name__ == '__main__':
    unittest.main()
