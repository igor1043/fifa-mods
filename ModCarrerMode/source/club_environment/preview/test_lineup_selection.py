import unittest
from lineup_selection import select

class Row:
    def __init__(self,**fields):self.fields=fields
    def value(self,key):return self.fields[key]

class LineupSelectionTests(unittest.TestCase):
    def setUp(self):
        self.players={i:Row(preferredposition1=0 if i==1 else 14,overallrating=70) for i in range(1,14)}
        self.sheet=Row(teamid=517,**{f'playerid{i}':i+1 for i in range(11)})
    def test_complete_saved_xi_is_unchanged(self):
        data=select(517,[],[self.sheet],self.players,set(self.players))
        self.assertEqual([s['id'] for s in data['slots']],list(range(1,12)));self.assertFalse(data['probable'])
    def test_departed_player_is_replaced_without_stealing_another_starter(self):
        self.sheet.fields['playerid0']=208670
        self.players[12].fields.update(preferredposition1=0,overallrating=80)
        data=select(517,[],[self.sheet],self.players,set(self.players)-{1})
        self.assertTrue(data['probable']);self.assertEqual(data['source'],'probable-roster');self.assertEqual(data['slots'][0]['id'],12)
        self.assertEqual([s['id'] for s in data['slots'][1:]],list(range(2,12)))
        self.assertEqual(len({s['id'] for s in data['slots']}),11)
    def test_another_valid_sheet_is_preferred_to_an_estimate(self):
        bad=Row(teamid=517,isfavourite=1,**{f'playerid{i}':-1 for i in range(11)})
        data=select(517,[bad],[self.sheet],self.players,set(self.players));self.assertFalse(data['probable'])
    def test_short_roster_returns_unavailable_without_fabricated_players(self):
        data=select(517,[],[self.sheet],self.players,{1,2,3});self.assertEqual(data['slots'],[])
    def test_duplicate_and_invalid_coordinates_are_repaired(self):
        self.sheet.fields.update(playerid1=1,offset0x=float('nan'),offset0y=2)
        data=select(517,[],[self.sheet],self.players,set(self.players));self.assertTrue(data['probable'])
        self.assertEqual(len({s['id'] for s in data['slots']}),11)
        self.assertTrue(all(0<=s['x']<=1 and 0<=s['y']<=1 for s in data['slots']))

if __name__=='__main__':unittest.main()
