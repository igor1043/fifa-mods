"""Venue titles must identify the host, not the stadium model it reuses."""
import tempfile
import unittest
from pathlib import Path
from preview_details import enrich,stadium_title
from test_preview_details import Row
from projection import TABLES


class StadiumTitleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.game=Path(self.temp.name);(self.game/'FSW').mkdir()
        self.tables={'stadiumassignments':[
            Row(teamid=101105,stadiumcustomname='Estádio El Campín'),
            Row(teamid=120433,stadiumcustomname='Estádio da Cidadania - RJ')]}

    def resolve(self,home=101105,league=0,base=None):
        return stadium_title(home,league,lambda name:self.tables.get(name,[]),
                             base or {},'_Stadion Hanguk',self.game)

    def settings(self,text,encoding='utf8'):
        (self.game/'FSW/settings.ini').write_text(text,encoding=encoding)

    def test_custom_name_is_read_from_the_correct_db_table(self):
        self.assertIn('stadiumassignments',TABLES)
        self.assertEqual(self.resolve()[0],'Estádio El Campín')

    def test_changing_host_replaces_title_even_with_the_same_stadium_model(self):
        self.assertEqual(self.resolve()[0],'Estádio El Campín')
        self.assertEqual(self.resolve(home=120433)[0],'Estádio da Cidadania - RJ')
        self.assertEqual(self.resolve()[0],'Estádio El Campín')

    def test_save_custom_name_beats_base_db_and_does_not_change_capacity(self):
        base={'stadiumassignments':[Row(teamid=101105,stadiumcustomname='Nome antigo')]}
        self.assertEqual(self.resolve(base=base)[0],'Estádio El Campín')
        payload={'date':20260324,'fixture':[1,0,0,20260324,2200,101105,10],
                 'user':{'team_id':10,'name':'Visitante','players':[]},
                 'opponent':{'team_id':101105,'name':'Millonarios','players':[]}}
        self.tables.update(teams=[Row(teamid=101105,teamname='Millonarios'),Row(teamid=10,teamname='Visitante')],
            teamstadiumlinks=[Row(teamid=101105,stadiumid=196)],
            stadiums=[Row(stadiumid=196,name='_Stadion Hanguk',capacity=55299)])
        details=enrich(payload,{'fixtures':[]},lambda name:self.tables.get(name,[]),base,game=self.game)['details']
        self.assertEqual(details['stadium'],'Estádio El Campín')
        self.assertEqual(details['capacity'],'55.299')
        self.assertEqual(details['home_name'],'Millonarios')

    def test_missing_save_assignment_uses_base_club_assignment(self):
        self.tables['stadiumassignments']=[]
        base={'stadiumassignments':[Row(teamid=101105,stadiumcustomname='El Campín atualizado')]}
        self.assertEqual(self.resolve(base=base)[0],'El Campín atualizado')

    def test_empty_or_conflicting_assignments_do_not_pick_an_arbitrary_name(self):
        for assigned in ([Row(teamid=101105,stadiumcustomname='  ')],
                         [Row(teamid=101105,stadiumcustomname='A'),Row(teamid=101105,stadiumcustomname='B')]):
            with self.subTest(assigned=assigned):
                self.tables['stadiumassignments']=assigned
                self.assertEqual(self.resolve()[0],'_Stadion Hanguk')

    def test_fsw_club_override_matches_native_card_and_keeps_stadium_alias(self):
        self.settings('[stadium]\n101105=Custom Ground,5,3,0\n[scoreboardstdname]\n'
                      'Custom Ground=Santa Cruz - Arena NicNet - Ribeirão Preto - SP,1\n')
        self.assertEqual(self.resolve(),('Santa Cruz - Arena NicNet','FSW/settings.ini [stadium]'))

    def test_competition_override_beats_club_and_does_not_claim_random_pool_choice(self):
        self.settings('[comp]\n269=Final A,Final B,Final C,5,3,0\n[stadium]\n101105=Clube,5,3,0\n'
                      '[scoreboardstdname]\nFinal A=Arena Á – Cidade – COL,1\nFinal B=Arena B,1\nFinal C=Arena C,1\n')
        self.assertEqual(self.resolve(league=269),('Arena Á - Arena B + outras opcoes','FSW/settings.ini [comp]'))

    def test_native_legacy_numeric_suffix_and_numbered_stadium_exact_key(self):
        self.settings('[comp]\n269=Arena5,3,0\n[scoreboardstdname]\nArena=Arena sem sufixo,1\n')
        self.assertEqual(self.resolve(league=269)[0],'Arena sem sufixo')
        self.settings('[comp]\n269=Arena5,3,0\n[scoreboardstdname]\nArena=Arena sem sufixo,1\nArena5=Arena 5,1\n')
        self.assertEqual(self.resolve(league=269)[0],'Arena 5')

    def test_encodings_and_case_insensitive_section_match_native_configuration(self):
        for encoding in ('utf8','cp1252','utf16'):
            with self.subTest(encoding=encoding):
                self.settings('[STADIUM]\n101105=El Campin,6,125,0\n[SCOREBOARDSTDNAME]\n'
                              'El Campin=Estadio El Campín – Bogotá – COL,1\n',encoding)
                self.assertEqual(self.resolve()[0],'Estadio El Campín')

    def test_no_settings_file_is_created_as_a_side_effect(self):
        self.resolve()
        self.assertFalse((self.game/'FSW/settings.ini').exists())


if __name__=='__main__':unittest.main(verbosity=2)
