"""Checks the generated selector, FIFA catalog, and reviewed club locations."""
import configparser
import json
import unittest
from pathlib import Path

from build_preview import load_sample_career
from fifa_db import catalog

ROOT = Path(__file__).resolve().parent


class ClubGlobeCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = configparser.ConfigParser(interpolation=None)
        config.read(ROOT / 'clubes.ini', encoding='utf-8-sig')
        cls.game = Path(config['fifa']['game_path'])
        cls.generated = json.loads((ROOT / 'clubes.json').read_text(encoding='utf-8'))
        cls.html = (ROOT / 'index.html').read_text(encoding='utf-8')
        cls.template = (ROOT / 'template.html').read_text(encoding='utf-8')

        installed = catalog(cls.game)
        cls.sample = load_sample_career(
            cls.game, config['fifa'].get('sample_save_slot', '').strip(), installed)
        leagues = cls.sample['leagues'] if cls.sample else installed
        eligible = [league for league in leagues
                    if league['leagueid'] != 78 and 1 <= league['level'] <= 7 and league['clubs']]
        memberships = {}
        for league in eligible:
            for team in league['clubs']:
                memberships.setdefault(team['teamid'], set()).add(league['leagueid'])
        cls.expected = {
            league['leagueid']: {
                team['teamid'] for team in league['clubs']
                if memberships[team['teamid']] == {league['leagueid']}
            }
            for league in eligible
        }
        cls.expected = {league_id: team_ids for league_id, team_ids in cls.expected.items() if team_ids}

    def test_every_native_eligible_primary_league_is_available(self):
        actual = {league['id']: {club['id'] for club in league['clubs']}
                  for league in self.generated['leagues']}
        self.assertEqual(actual, self.expected)
        self.assertGreaterEqual(len(actual), 90)
        self.assertGreaterEqual(len(self.generated['countries']), 35)
        self.assertGreaterEqual(sum(map(len, actual.values())), 1500)

    def test_startup_selects_the_sample_save_club(self):
        league = next(item for item in self.generated['leagues']
                      if item['id'] == self.generated['defaultLeagueId'])
        selected = next(club for club in league['clubs']
                        if club['id'] == self.generated['defaultTeamId'])
        if self.sample:
            self.assertEqual(self.generated['sampleSaveSlot'], self.sample['slot'])
            self.assertEqual(selected['id'], self.sample['club_id'])
            self.assertEqual(league['countryId'], self.generated['defaultCountryId'])
        self.assertTrue(selected['city'])

    def test_bolivia_japan_and_romania_cities_and_positions_are_reviewed(self):
        cases = {
            12: {
                130903: 'El Alto', 120087: 'Cochabamba', 130038: 'Santa Cruz de la Sierra',
                120079: 'La Paz', 130201: 'Montero', 120047: 'Sucre',
                130032: 'Cochabamba', 130202: 'Potosí', 120082: 'Santa Cruz de la Sierra',
                130034: 'Santa Cruz de la Sierra', 120084: 'Tarija',
                130031: 'Santa Cruz de la Sierra', 130243: 'Bulo Bulo (Entre Ríos)',
                120042: 'Oruro', 120086: 'La Paz', 130400: 'Vinto',
            },
            349: {
                130222: 'Niigata', 130323: 'Fukuoka', 112345: 'Osaka', 101150: 'Tokyo',
                112093: 'Suita', 113186: 'Sapporo', 101147: 'Kashima', 101145: 'Kashiwa',
                111730: 'Kawasaki', 113162: 'Kyoto', 130402: 'Machida', 112092: 'Nagoya',
                113160: 'Tosu', 113157: 'Hiroshima', 113161: 'Hiratsuka', 130401: 'Tokyo',
                111575: 'Saitama', 101146: 'Kobe', 101151: 'Yokohama', 113197: 'Yokohama',
            },
            330: {
                110078: 'Ploiești', 130375: 'Slobozia', 114385: 'Cluj-Napoca',
                130394: 'Iași', 110752: 'Botoșani', 100757: 'Bucharest',
                130410: 'Buzău', 130353: 'Sibiu', 114147: 'Bucharest',
                110750: 'Arad', 110751: 'Cluj-Napoca', 100761: 'Bucharest',
                110815: 'Constanța', 110072: 'Galați', 113378: 'Sfântu Gheorghe',
                308: 'Craiova',
            },
        }
        for league_id, expected in cases.items():
            league = next(item for item in self.generated['leagues'] if item['id'] == league_id)
            actual = {club['id']: club for club in league['clubs']}
            self.assertEqual(set(actual), set(expected))
            for team_id, city in expected.items():
                self.assertEqual(actual[team_id]['city'], city)
                self.assertTrue(-90 <= actual[team_id]['lat'] <= 90)
                self.assertTrue(-180 <= actual[team_id]['lon'] <= 180)
        bolivia = {club['id']: club for club in next(
            item for item in self.generated['leagues'] if item['id'] == 12)['clubs']}
        self.assertEqual((bolivia[130903]['lat'], bolivia[130903]['lon']), (-16.5048, -68.1624))
        self.assertEqual((bolivia[130243]['lat'], bolivia[130243]['lon']), (-17.25412, -64.36429))
        japan = {club['id']: club for club in next(
            item for item in self.generated['leagues'] if item['id'] == 349)['clubs']}
        self.assertEqual((japan[113186]['lat'], japan[113186]['lon']), (43.06667, 141.35))

    def test_country_and_league_icons_are_bundled(self):
        for country in self.generated['countries']:
            self.assertTrue(country['icon'], country['name'])
            self.assertTrue((ROOT / country['icon']).is_file(), country['icon'])
        for league in self.generated['leagues']:
            self.assertTrue(league['icon'], league['id'])
            self.assertTrue((ROOT / league['icon']).is_file(), league['icon'])

    def test_every_available_crest_is_bundled_locally(self):
        clubs = [club for league in self.generated['leagues'] for club in league['clubs']]
        self.assertEqual(len(clubs), sum(map(len, self.expected.values())))
        missing = []
        for club in clubs:
            if not club['crest']:
                missing.append(club['id'])
                continue
            self.assertTrue((ROOT / club['crest']).is_file(), club['crest'])
        self.assertEqual(len(missing), 3)

    def test_page_is_dark_and_has_three_stacked_carousels(self):
        self.assertNotIn('__FF_', self.html)
        self.assertNotIn('<script src=', self.html.lower())
        self.assertIn('grid-template-columns:minmax(280px,1fr) minmax(0,2fr)', self.template)
        self.assertIn('color-scheme:dark', self.template)
        self.assertIn('data-step-country', self.template)
        self.assertIn('data-step-league', self.template)
        self.assertIn('data-step-team', self.template)
        self.assertIn('data-team-location', self.template)
        self.assertNotIn('<select', self.template.lower())
        self.assertNotIn('ff-footer', self.template)
        for old_label in ('Protótipo', 'catálogo e escudos', 'Mapa de países'):
            self.assertNotIn(old_label.casefold(), self.template.casefold())
        self.assertIn('class="ff-pin"', self.template)


if __name__ == '__main__':
    unittest.main(verbosity=2)
