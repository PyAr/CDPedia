# -*- coding: utf8 -*-

# Copyright 2015-2020 CDPedistas (see AUTHORS.txt)
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

from src.scrapping import portals


class ESParsingTests(unittest.TestCase):
    """Test how parsing works."""

    def _get_data(self, pos):
        with open("tests/fixtures/portals-es.html", "rb") as fh:
            html = fh.read()
        items = portals.parse('es', html)
        self.assertEqual(len(items), 8)
        return items[pos]

    def test_simple(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(0)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "5/5e/P_social_sciences.png/35px-P_social_sciences.png"))

        self.assertEqual(titles, [
            ("Ciencias humanas y sociales", "/wiki/Portal:Ciencias_humanas_y_sociales"),
        ])
        self.assertEqual(sub_simples, [
            ("Antropología", "/wiki/Portal:Antropolog%C3%ADa"),
            ("Derecho", "/wiki/Portal:Derecho"),
            ("Economía", "/wiki/Portal:Econom%C3%ADa"),
            ("Contabilidad", "/wiki/Portal:Contabilidad"),
            ("Educación", "/wiki/Portal:Educaci%C3%B3n"),
            ("Filosofía", "/wiki/Portal:Filosof%C3%ADa"),
            ("Psicología", "/wiki/Portal:Psicolog%C3%ADa"),
            ("Sociología", "/wiki/Portal:Sociolog%C3%ADa"),
            ("Feminismo", "/wiki/Portal:Feminismo"),
        ])
        c1, c2 = sub_complexes
        titles, items = c1
        self.assertEqual(titles, [
            ("Ciencia política", "/wiki/Portal:Ciencia_pol%C3%ADtica"),
        ])
        self.assertEqual(items, [
            ("Euskal Herria", "/wiki/Portal:Euskal_Herria"),
            ("Marxismo", "/wiki/Portal:Marxismo"),
            ("Nacionalismo", "/wiki/Portal:Nacionalismo"),
            ("Nacionalismo catalán", "/wiki/Portal:Nacionalismo_catal%C3%A1n"),
            ("Nacionalismo gallego", "/wiki/Portal:Nacionalismo_gallego"),
            ("Nacionalismo vasco", "/wiki/Portal:Nacionalismo_vasco"),
            ("Militar", "/wiki/Portal:Militar"),
            ("Naciones Unidas", "/wiki/Portal:Naciones_Unidas"),
            ("OTAN", "/wiki/Portal:OTAN"),
            ("Socialdemocracia", "/wiki/Portal:Socialdemocracia"),
            ("Socialismo", "/wiki/Portal:Socialismo"),
            ("Terrorismo", "/wiki/Portal:Terrorismo"),
            ("Unión Europea", "/wiki/Portal:Uni%C3%B3n_Europea"),
        ])
        titles, items = c2
        self.assertEqual(titles, [
            ("Lingüística", "/wiki/Portal:Ling%C3%BC%C3%ADstica"),
        ])
        self.assertEqual(items, [
            ("Lenguas", "/wiki/Portal:Lenguas"),
            ("Lengua asturiana", "/wiki/Portal:Lengua_asturiana"),
            ("Lengua catalana", "/wiki/Portal:Lengua_catalana"),
            ("Lengua española", "/wiki/Portal:Lengua_espa%C3%B1ola"),
            ("Esperanto", "/wiki/Portal:Esperanto"),
            ("Lengua aragonesa", "/wiki/Portal:Lengua_aragonesa"),
            ("Lenguas portuguesa y gallega", "/wiki/Portal:Lenguas_portuguesa_y_gallega"),
            ("Lenguas indígenas de América",
                "/wiki/Portal:Lenguas_ind%C3%ADgenas_de_Am%C3%A9rica"),
            ("Lengua Ido", "/wiki/Portal:Ido"),
        ])

    def test_no_linked_complex_title(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(1)
        self.assertEqual(titles, [
            ("Ciencias naturales y formales", "/wiki/Portal:Ciencias_naturales_y_formales"),
        ])
        self.assertEqual(sub_simples, [])
        titles, items = sub_complexes[1]  # the one with a title with no link
        self.assertEqual(titles, [
            ("Ciencias naturales", None),
        ])
        self.assertEqual(items, [
            ("Astronomía", "/wiki/Portal:Astronom%C3%ADa"),
            ("Ciclones tropicales", "/wiki/Portal:Ciclones_tropicales"),
            ("Cosmología", "/wiki/Portal:Cosmolog%C3%ADa"),
            ("Física", "/wiki/Portal:F%C3%ADsica"),
            ("Química", "/wiki/Portal:Qu%C3%ADmica"),
            ("Sistema Solar", "/wiki/Portal:Sistema_Solar"),
        ])

    def test_double_title_no_complex(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(5)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "d/d9/P_religion.png/35px-P_religion.png"))

        self.assertEqual(titles, [
            ("Religión", "/wiki/Portal:Religi%C3%B3n"),
            ("Mitología", "/wiki/Portal:Mitolog%C3%ADa"),
        ])
        self.assertEqual(sub_simples, [
            ("Ateísmo", "/wiki/Portal:Ate%C3%ADsmo"),
            ("Budismo", "/wiki/Portal:Budismo"),
            ("Cristianismo", "/wiki/Portal:Cristianismo"),
            ("Cristianismo evangélico", "/wiki/Portal:Cristianismo_evang%C3%A9lico"),
            ("Hinduismo", "/wiki/Portal:Hinduismo"),
            ("Iglesia católica", "/wiki/Portal:Iglesia_cat%C3%B3lica"),
            ("Islam", "/wiki/Portal:Islam"),
            ("Esoterismo", "/wiki/Portal:Esoterismo"),
            ("Judaísmo", "/wiki/Portal:Juda%C3%ADsmo"),
            ("Judaísmo mesiánico", "/wiki/Portal:Juda%C3%ADsmo_mesi%C3%A1nico"),
            ("Leyendas Urbanas", "/wiki/Portal:Leyendas_Urbanas"),
            ("Santos", "/wiki/Portal:Santos"),
            ("Wicca", "/wiki/Portal:Wicca"),
            ("Neopaganismo", "/wiki/Portal:Neopaganismo"),
        ])
        self.assertEqual(len(sub_complexes), 0)

    def test_double_complex_title__no_link_title(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(3)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "b/b4/P_art.png/35px-P_art.png"))

        self.assertEqual(titles, [
            ("Cultura y sociedad", None),
        ])
        titles, items = sub_complexes[2]
        self.assertEqual(titles, [
            ("Cine", "/wiki/Portal:Cine"),
            ("Televisión", "/wiki/Portal:Televisi%C3%B3n"),
            ("Historieta", "/wiki/Portal:Historieta"),
        ])
        self.assertEqual(items, [
            ("Anime y Manga", "/wiki/Portal:Anime_y_Manga"),
            ("DC Comics", "/wiki/Portal:DC_Comics"),
            ("Disney", "/wiki/Portal:Disney"),
            ("Doctor Who", "/wiki/Portal:Doctor_Who"),
            ("Futurama", "/wiki/Portal:Futurama"),
            ("James Bond", "/wiki/Portal:James_Bond"),
            ("Los Simpson", "/wiki/Portal:Los_Simpson"),
            ("Marvel Comics", "/wiki/Portal:Marvel_Comics"),
            ("Sonic the Hedgehog", "/wiki/Portal:Sonic_the_Hedgehog"),
            ("Telenovelas", "/wiki/Portal:Telenovelas"),
        ])

    def test_sub_section(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(7)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "8/8e/P_countries-vector.svg/35px-P_countries-vector.svg.png"))

        self.assertEqual(titles, [
            ("Geografía", "/wiki/Portal:Geograf%C3%ADa"),
        ])
        self.assertEqual(sub_simples, [
            ("Antártida", "/wiki/Portal:Ant%C3%A1rtida"),
            ("Ártico", "/wiki/Portal:%C3%81rtico"),
            ("Medio Rural", "/wiki/Portal:Rural"),
            ("Países", "/wiki/Portal:Pa%C3%ADses"),
        ])

        titles, items = sub_complexes[0]
        self.assertEqual(titles, [("África", "/wiki/Portal:%C3%81frica")])
        self.assertEqual(items, [])
        titles, items = sub_complexes[1]
        self.assertEqual(titles, [("América", "/wiki/Portal:Am%C3%A9rica")])
        self.assertEqual(items, [
            ("Argentina", "/wiki/Portal:Argentina"),
            ("Canadá", "/wiki/Portal:Canad%C3%A1"),
            ("Chile", "/wiki/Portal:Chile"),
            ("Colombia", "/wiki/Portal:Colombia"),
            ("Ecuador", "/wiki/Portal:Ecuador"),
            ("Estados Unidos", "/wiki/Portal:Estados_Unidos_de_Am%C3%A9rica"),
            ("México", "/wiki/Portal:M%C3%A9xico"),
            ("Perú", "/wiki/Portal:Per%C3%BA"),
        ])
        titles, items = sub_complexes[2]
        self.assertEqual(titles, [("Asia", "/wiki/Portal:Asia")])
        self.assertEqual(items, [
            ("China", "/wiki/Portal:China"),
            ("Israel", "/wiki/Portal:Israel"),
        ])
        titles, items = sub_complexes[3]
        self.assertEqual(titles, [("Europa", "/wiki/Portal:Europa")])
        self.assertEqual(items, [
            ("Unión Europea", "/wiki/Portal:Uni%C3%B3n_Europea"),
            ("España", "/wiki/Portal:Espa%C3%B1a"),
            ("Reino Unido", "/wiki/Portal:Reino_Unido"),
            ("Rusia", "/wiki/Portal:Rusia"),
        ])
        titles, items = sub_complexes[4]
        self.assertEqual(titles, [("Oceanía", "/wiki/Portal:Ocean%C3%ADa")])
        self.assertEqual(items, [
            ("Australia", "/wiki/Portal:Australia"),
        ])


class PTParsingTests(unittest.TestCase):
    """Test how parsing works."""
    maxDiff = None

    def _get_data(self, pos):
        with open("tests/fixtures/portals-pt.html", "rb") as fh:
            html = fh.read()
        items = portals.parse('pt', html)
        self.assertEqual(len(items), 8)
        return items[pos]

    def test_multiple_levels(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(0)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "c/ca/Nuvola_apps_kcoloredit.png/40px-Nuvola_apps_kcoloredit.png"))

        self.assertEqual(titles, [
            ("Arte", "/wiki/Portal:Arte"),
            ("Entretenimento", "/wiki/Portal:Entretenimento"),
        ])
        self.assertEqual(sub_simples, [])

        titles, items = sub_complexes[0]
        self.assertEqual(titles, [
            ("Arte", None),
        ])
        self.assertEqual(items, [
            ("Arquitetura e Urbanismo", "/wiki/Portal:Arquitetura_e_Urbanismo"),
            ("Banda Desenhada", "/wiki/Portal:Banda_desenhada"),
            ("Cinema", "/wiki/Portal:Cinema"),
            ("Cores", "/wiki/Portal:Cores"),
            ("Dança", "/wiki/Portal:Dan%C3%A7a"),
            ("Fotografia", "/wiki/Portal:Fotografia"),
            ("Literatura", "/wiki/Portal:Literatura"),
            ("Moda", "/wiki/Portal:Moda"),
            ("Teatro", "/wiki/Portal:Teatro"),
        ])

        titles, items = sub_complexes[1]
        self.assertEqual(titles, [
            ("Literatura e Cinema", None),
        ])
        self.assertEqual(items, [
            ("Academia Brasileira de Letras", "/wiki/Portal:Academia_Brasileira_de_Letras"),
            ("As Crônicas de Nárnia", "/wiki/Portal:As_Cr%C3%B4nicas_de_N%C3%A1rnia"),
            ("Cartoon Network", "/wiki/Portal:Cartoon_Network"),
            ("Disney", "/wiki/Portal:Disney"),
            ("Ficção científica", "/wiki/Portal:Fic%C3%A7%C3%A3o_cient%C3%ADfica"),
            ("Harry Potter", "/wiki/Portal:Harry_Potter"),
            ("Percy Jackson", "/wiki/Portal:Percy_Jackson"),
            ("Saga Crepúsculo", "/wiki/Portal:Twilight"),
            ("Terra-média", "/wiki/Portal:Terra-M%C3%A9dia"),
            ("The Hunger Games", "/wiki/Portal:The_Hunger_Games"),
            ("The Walking Dead", "/wiki/Portal:The_Walking_Dead"),
        ])

        titles, items = sub_complexes[4]
        self.assertEqual(titles, [
            ("Música", "/wiki/Portal:M%C3%BAsica"),
        ])
        self.assertEqual(items, [])
        titles, items = sub_complexes[5]
        self.assertEqual(titles, [
            ("Gêneros", None),
        ])
        self.assertEqual(items, [
            ("Alternativa", "/wiki/Portal:M%C3%BAsica_alternativa"),
            ("Blues", "/wiki/Portal:Blues"),
            ("Erudita", "/wiki/Portal:M%C3%BAsica_Cl%C3%A1ssica"),
            ("Heavy metal", "/wiki/Portal:Heavy_metal"),
            ("Hip hop", "/wiki/Portal:Hip_hop"),
            ("Jazz", "/wiki/Portal:Jazz"),
            ("Portuguesa", "/wiki/Portal:M%C3%BAsica_Portuguesa"),
            ("Pop", "/wiki/Portal:M%C3%BAsica_pop"),
            ("Punk rock", "/wiki/Portal:Punk_rock"),
            ("Rock", "/wiki/Portal:Rock"),
            ("R&B", "/wiki/Portal:R%26B"),
        ])

        titles, items = sub_complexes[8]
        self.assertEqual(titles, [
            ("Entretenimento", None),
        ])
        self.assertEqual(items, [
            ("Carnaval", "/wiki/Portal:Carnaval"),
        ])

        titles, items = sub_complexes[9]
        self.assertEqual(titles, [
            ("Jogos", None),
        ])
        self.assertEqual(items, [
            ("Enxadrismo", "/wiki/Portal:Xadrez"),
            ("Final Fantasy", "/wiki/Portal:Final_Fantasy"),
            ("Jogos", "/wiki/Portal:Jogos"),
            ("Jogos eletrônicos", "/wiki/Portal:Jogos_eletr%C3%B4nicos"),
            ("Level Up! Games", "/wiki/Portal:Level_Up!_Games"),
            ("Pokémon", "/wiki/Portal:Pok%C3%A9mon"),
            ("RPG", "/wiki/Portal:RPG"),
            ("Sega", "/wiki/Portal:Sega"),
        ])

    def test_simple(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(7)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "9/9a/Nuvola_apps_display.png/40px-Nuvola_apps_display.png"))

        self.assertEqual(titles, [
            ("Tecnologia", "/wiki/Portal:Tecnologia"),
        ])
        self.assertEqual(sub_simples, [
            ("Eletrônica", "/wiki/Portal:Eletr%C3%B4nica"),
            ("Linux", "/wiki/Portal:Linux"),
            ("Rádio", "/wiki/Portal:R%C3%A1dio"),
            ("Software Livre", "/wiki/Portal:Software_Livre"),
            ("Tecnologias de informação", "/wiki/Portal:Tecnologias_de_informa%C3%A7%C3%A3o"),
            ("Transportes", "/wiki/Portal:Transporte"),
            ("Aviação", "/wiki/Portal:Avia%C3%A7%C3%A3o"),
            ("Náutico", "/wiki/Portal:N%C3%A1utico"),
        ])
        titles, items = sub_complexes[0]
        self.assertEqual(titles, [
            ("Empresas", None),
        ])
        self.assertEqual(items, [
            ("Apple", "/wiki/Portal:Apple_Inc."),
            ("Google", "/wiki/Portal:Google"),
            ("Microsoft", "/wiki/Portal:Microsoft"),
        ])

    def test_non_empty(self):
        icon, titles, sub_simples, sub_complexes = self._get_data(1)
        self.assertEqual(icon, (
            "//upload.wikimedia.org/wikipedia/commons/thumb/"
            "f/f5/Nuvola_apps_kalzium.png/40px-Nuvola_apps_kalzium.png"))

        self.assertEqual(titles, [
            ("Ciências", "/wiki/Portal:Ci%C3%AAncia"),
            ("Saúde", "/wiki/Portal:Sa%C3%BAde"),
        ])
        self.assertEqual(sub_simples, [])
        self.assertEqual(len(sub_complexes), 3)
        self.assertEqual(sub_complexes[0][0], [("Exatas", None)])
        self.assertEqual(sub_complexes[1][0], [("Biológicas", None)])
        self.assertEqual(sub_complexes[2][0], [("Saúde", None)])
