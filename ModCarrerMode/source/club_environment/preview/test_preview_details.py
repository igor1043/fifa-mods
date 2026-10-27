import portable_paths as portable
import unittest
from preview_details import contrast,recent,enrich,fixture_competition

class Row:
    def __init__(self,**values):self.fields=values
    def value(self,k):return self.fields[k]

class DetailsTests(unittest.TestCase):
    def test_white_header_black_text_and_black_header_white_text(self):
        self.assertEqual(contrast((255,255,255)),0x182830)
        self.assertEqual(contrast((0,0,0)),0xffffff)
        self.assertEqual(contrast((230,0,0)),0xffffff)
        self.assertEqual(contrast((255,255,0)),0x182830)
    def test_history_filters_unplayed_and_keeps_team_perspective(self):
        fixtures=[[1,0,0,20260101,1600,10,20,2,1,1],
                  [2,0,0,20260102,1600,20,10,3,1,1],
                  [3,0,0,20260103,1600,10,20,-1,-1,0],
                  [4,0,0,20260105,1600,10,20,9,0,1],
                  [5,0,0,20260103,1700,20,30,0,1,1]]
        games=recent(fixtures,10,20260103,{20:'Rival'})
        self.assertEqual([g['fixture'] for g in games],[2,1])
        self.assertEqual([(g['score'],g['result'],g['venue']) for g in games],[('1 – 3','D','Fora'),('2 – 1','V','Casa')])
    def test_missing_stadium_and_history_do_not_fabricate_information(self):
        p={'date':20260101,'fixture':[1,0,0,20260101,2130,10,20],
           'user':{'team_id':10,'name':'A','players':[]},'opponent':{'team_id':20,'name':'B','players':[]}}
        teams=[Row(teamid=10,teamname='A',teamcolor1r=255,teamcolor1g=255,teamcolor1b=255),Row(teamid=20,teamname='B')]
        result=enrich(p,{'fixtures':[]},lambda name:teams if name=='teams' else [],{})
        self.assertEqual(result['details']['stadium'],'Não informado');self.assertEqual(result['details']['capacity'],'Não informada')
        self.assertEqual(result['user']['recent'],[]);self.assertEqual(result['user']['header_ink'],0x182830)
        self.assertEqual(result['details']['time'],'21:30')
    def test_each_result_resolves_its_own_competition_parent(self):
        fixtures=[[1,101,0,20260101,1600,10,20,2,1,1],
                  [2,201,0,20260102,1600,20,10,1,1,1],
                  [3,301,0,20260103,1600,10,20,3,1,1]]
        nodes={101:[101,100,5,0],100:[100,0,3,7],
               201:[201,200,5,0],200:[200,0,3,13],
               301:[301,302,5,0],302:[302,301,5,0]}
        games=recent(fixtures,10,20260103,{20:'Rival'},nodes=nodes,competition_label=lambda ident:{7:'Liga',13:'Copa'}[ident])
        self.assertEqual([g['competition_id'] for g in games],[0,13,7])
        self.assertEqual([g['competition'] for g in games],['Competição não informada','Copa','Liga'])
        self.assertEqual(fixture_competition([9,999],nodes),0)
if __name__=='__main__':unittest.main(verbosity=2)
