"""Regression contract for career-tab moves using the working installed hub."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE/'tools'))
import reorganize_career_hub as hub


class CareerHubReorganization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (Path(__file__).parent/'fixtures/career_hub_before_reorganization.xml').read_bytes()
        with mock.patch.object(hub, 'refine', side_effect=lambda raw: raw):
            cls.v1 = hub.reorganize(cls.raw)
        cls.result = hub.reorganize(cls.raw)

    def setUp(self):
        self.before = ET.fromstring(self.raw)
        self.after = ET.fromstring(self.result)

    def card(self, panel, name):
        return hub.tile(self.after.find(f'panel_{panel}'), name)

    def test_reapplying_is_byte_idempotent(self):
        self.assertEqual(hub.reorganize(self.result), self.result)

    def test_all_callback_counts_are_preserved(self):
        self.assertEqual(hub.destinations(self.before), hub.destinations(self.after))

    def test_mod_destinations_are_in_their_approved_tabs(self):
        for event, tab in [('Server16EnterManagerMarket', 2), ('Server16EnterTransferMarket', 2),
                           ('Server16EnterClubFinance', 3), ('Server16EnterBankLoans', 3),
                           ('Server16EnterDressingRoom', 7), ('Server16EnterClubBrowser', 4),
                           ('Server16EnterCareerCompetitions', 5), ('Server16EnterMatchPreview', 0)]:
            owners = [p.tag for p in self.after if p.tag.startswith('panel_')
                      for n in p.iter() if n.get('DESTINATION') == event]
            self.assertEqual(owners, [f'panel_{tab}'])

    def test_squad_and_competitions_are_unchanged(self):
        for name in ('hub_settings', 'components', 'buttons', 'resolution', 'panel_set',
                     'panel_1', 'panel_5', 'panel_6'):
            self.assertEqual(ET.tostring(self.before.find(name)), ET.tostring(self.after.find(name)))

    def test_calendar_and_season_news_are_unchanged(self):
        for name in ('CALENDAR', 'NEWS', 'RSS'):
            old = hub.tile(self.before.find('panel_4'), name)
            self.assertEqual(ET.tostring(old), ET.tostring(self.card(4, name)))

    def test_native_scout_variants_only_move_position(self):
        for ident in ('208', '215'):
            def find(root):
                return next(t for t in root.find('panel_2').findall('tile')
                            if t.find('tileid').get('tileid') == ident)
            old, new = deepcopy(find(self.before)), deepcopy(find(self.after))
            self.assertEqual(new.find('settings').get('WIDTH'), '846')
            self.assertEqual(new.find('settings').get('HEIGHT'), '418')
            for key in ('X', 'Y'):
                old.find('settings').attrib.pop(key)
                new.find('settings').attrib.pop(key)
            self.assertEqual(ET.tostring(old), ET.tostring(new))

    def test_deal_components_keep_exact_ids_provider_and_readable_geometry(self):
        market = self.card(2, 'GTN_STATIC')
        self.assertEqual([market.find('settings').get(k) for k in ('WIDTH', 'HEIGHT')], ['846', '632'])
        for ident in ('529', '530'):
            old = next(n for n in self.before.iter() if n.get('ID') == ident)
            new = next(n for n in market if n.get('ID') == ident)
            self.assertEqual(ET.tostring(old), ET.tostring(new))
            self.assertEqual(len([n for n in new if n.get('TYPE') == 'component']), 10)
        central = self.card(0, 'NEXT_MATCH_CENTRAL')
        self.assertEqual([p.get('ID') for p in hub.pages(central)], ['725', '728'])

    def test_finance_starts_with_dashboard_and_keeps_live_native_budget(self):
        finance = self.card(3, 'REQUEST_FUNDS')
        content = hub.pages(finance)
        self.assertEqual([p.get('DESTINATION') for p in content],
                         ['Server16EnterClubFinance', 'Server16EnterBankLoans',
                          'EnterBudgetAlloc', 'EnterAdditionalFunds'])
        budget = content[2]
        self.assertEqual(budget.get('DATAPROVIDERID'), 'CM_FINANCES_DP')
        self.assertEqual(budget.get('ID'), '256')
        for key in ('TRANSFERBUGET', 'WAGEBUGET'):
            self.assertIsNotNone(budget.find(f"data[@ID='{key}']"))
        self.assertFalse(any(n.get('DATAPROVIDERID') for n in finance.findall('tileid')))

    def test_dressing_room_is_second_and_summary_keeps_its_data_and_focus(self):
        card = self.card(7, 'MY_TEAM_CLUB')
        content = hub.pages(card)
        self.assertEqual(content[1].get('DESTINATION'), 'Server16EnterDressingRoom')
        self.assertEqual(content[0].get('HIGHLIGHTABLE'), 'TRUE')
        self.assertEqual(content[1].get('HIGHLIGHTABLE'), 'TRUE')
        original = hub.pages(hub.tile(self.before.find('panel_7'), 'MY_TEAM_CLUB'))[0]
        summary = content[0]
        original.set('HIGHLIGHTABLE', 'TRUE')
        original.tag = summary.tag
        self.assertEqual(ET.tostring(original), ET.tostring(summary))
        self.assertEqual(card.find('settings').get('WIDTH'), '1702')

    def test_clubs_reuses_the_team_statistics_slot_and_original_image(self):
        clubs = self.card(4, 'SERVER16_CLUB_BROWSER')
        old = hub.tile(self.before.find('panel_4'), 'TEAM_STATS')
        for key in ('X', 'Y', 'WIDTH', 'HEIGHT'):
            self.assertEqual(clubs.find('settings').get(key), old.find('settings').get(key))
        original = next(n for n in self.before.find('panel_4').iter()
                        if n.get('DESTINATION') == 'Server16EnterClubBrowser')
        current = hub.pages(clubs)[0]
        original.tag = current.tag
        self.assertEqual(ET.tostring(original), ET.tostring(current))
        other = self.card(4, 'OTHER_LEAGUES')
        self.assertEqual(len(hub.pages(other)), 1)
        self.assertEqual(other.find('main_tile').get('DESTINATION'), 'ViewOtherCompetitions')

    def test_player_and_team_statistics_share_the_lower_carousel(self):
        card = self.card(4, 'PLAYER_STATS')
        content = hub.pages(card)
        self.assertEqual([p.get('DESTINATION') for p in content], ['SelectStat', 'EnterTeamStats'])
        self.assertEqual([p.get('ID') for p in content], ['432', '416'])
        for name, new in zip(('PLAYER_STATS', 'TEAM_STATS'), content):
            old = hub.pages(hub.tile(self.before.find('panel_4'), name))[0]
            self.assertEqual([ET.tostring(n) for n in old.findall('data')],
                             [ET.tostring(n) for n in new.findall('data')])

    def test_coach_card_uses_short_title_without_reducing_font_or_changing_icon(self):
        card = self.card(2, 'SERVER16_MANAGER_MARKET')
        title = card.find("data[@ID='TITLE']")
        self.assertEqual(title.get('PARAM'), 'M. TÉCNICOS')
        self.assertEqual(title.get('FORMAT'), 'HS')
        self.assertEqual(card.find('main_tile').get('BG_ICON'), 'GlobalTransferNetwork_Med')

    def test_large_market_icons_keep_original_dds_pair_and_size_at_the_top(self):
        for slide in hub.pages(self.card(2, 'GTN_STATIC'))[:2]:
            self.assertNotIn('BG_ICON', slide.attrib)
            icons = [n for n in slide if n.get('TYPE') == 'image']
            self.assertEqual([n.get('PATH') for n in icons],
                ['imgAssets/tileIcons/ti_globaltransfernetwork_med_active.dds',
                 'imgAssets/tileIcons/ti_globaltransfernetwork_med_nonactive.dds'])
            self.assertEqual([(n.get('WIDTH'), n.get('HEIGHT'), n.get('Y')) for n in icons],
                             [('292', '204', '18')]*2)
            self.assertEqual([(n.get('HLALPHA'), n.get('UHLALPHA')) for n in icons],
                             [('100', '0'), ('0', '100')])
            for field in slide.findall('data'):
                if field.get('TYPE') in ('text', 'title'):
                    self.assertLessEqual(int(field.get('X'))+int(field.get('WIDTH')), 536)

    def test_compact_card_images_are_unchanged_by_the_refinement(self):
        previous = ET.fromstring(self.v1)
        for name in ('SHOPPING_LIST', 'SERVER16_MANAGER_MARKET'):
            old = hub.pages(hub.tile(previous.find('panel_2'), name))
            new = hub.pages(self.card(2, name))
            self.assertEqual([(n.get('FG_PATH'), n.get('BG_ICON')) for n in old],
                             [(n.get('FG_PATH'), n.get('BG_ICON')) for n in new])

    def test_v1_upgrade_is_equivalent_to_fresh_reorganization(self):
        self.assertEqual(hub.reorganize(self.v1), self.result)

    def test_browser_packager_preserves_the_standalone_clubs_card(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('browser_package_contract', SOURCE/'club_browser/package.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.carousel(self.result), self.result)

    def test_native_player_actions_keep_ids_and_shortlist_disabled_help(self):
        actions = hub.pages(self.card(2, 'SHOPPING_LIST'))
        self.assertEqual([p.get('ID') for p in actions], ['241', '242', '243', '272', '273'])
        self.assertEqual(actions[2].get('TILE_STATE'), 'DISABLED')
        self.assertIsNotNone(actions[2].find("data[@ID='DESC_DISABLED']"))
        self.assertTrue(all(p.get('FG_PATH') == '' for p in actions))
        self.assertTrue(all(p.get('BG_ICON') for p in actions))

    def test_geometry_and_carousel_counts_are_valid(self):
        hub.validate(self.after)

    def test_validator_rejects_overlapping_cards(self):
        self.card(2, 'SERVER16_MANAGER_MARKET').find('settings').set('X', '965')
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            hub.validate(self.after)

    def test_validator_rejects_missing_or_duplicated_routes(self):
        self.card(2, 'SERVER16_MANAGER_MARKET').find('main_tile').set('DESTINATION', 'WrongEvent')
        with self.assertRaisesRegex(ValueError, 'Incorrect career destination'):
            hub.validate(self.after)

    def test_validator_rejects_carousel_count_mismatch(self):
        self.card(2, 'GTN_STATIC').find('number_of_subtiles').set('LENGTH', '1')
        with self.assertRaisesRegex(ValueError, 'Incorrect carousel count'):
            hub.validate(self.after)

    def test_every_original_slide_id_survives(self):
        def ids(root):
            return Counter(n.get('ID') for t in root.iter('tile') for n in t
                           if n.tag == 'main_tile' or n.tag.startswith('subtile'))
        old, new = ids(self.before), ids(self.after)
        old.pop(None, None)
        self.assertFalse(old-new)


if __name__ == '__main__':
    unittest.main()
