# -*- coding: utf-8 -*-
import os
import sys
import unittest

from src import third_party # Need this to import werkzeug
from src.web import web_app, searcher

from werkzeug.test import Client
from werkzeug.wrappers import Request, Response


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

    def test_search_get(self):
        response = self.client.get("/search")
        self.assertEqual(response.status_code, 200)

    def test_search_post_url(self):
        response = self.client.post("/search")
        self.assertEqual(response.status_code, 302)

    def test_search_post(self):
        response = self.client.post("/search", data={"keywords":"a"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/search/" in response.location)
        response = self.client.post("/search", data={"keywords":"a"},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_search_term(self):
        response = self.client.post("/search", data={"keywords":"a"},
                                    follow_redirects=True)


if __name__ == '__main__':
    unittest.main()
