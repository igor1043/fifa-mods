import unittest
from board_confidence import for_spell
from career_profile import build

class BoardAndCareerTest(unittest.TestCase):
 def test_confidence_is_inverse_of_own_spell_pressure_and_stays_bounded(self):
  old=dict(game_date=20260110,pressure=90,reason='Antecessor')
  self.assertEqual(75,for_spell([old],20260110,20260110)['value'])
  reviews=[old,dict(game_date=20260120,pressure=43.6,reason='Classificação')];self.assertEqual(56,for_spell(reviews,20260110,20260120)['value'])
  self.assertEqual(0,for_spell([dict(old,pressure=180)],20260101,20260120)['value']);self.assertEqual(100,for_spell([dict(old,pressure=-15)],20260101,20260120)['value'])
 def test_career_history_preserves_clubs_spells_home_away_and_titles(self):
  person=dict(coach_id='coach');clubs={1:dict(name='Primeiro clube'),2:dict(name='Segundo clube')}
  def appointment(ident,club,start,end=None,reason=None,renewal=False):return dict(id=ident,coach_id='coach',club_id=club,start_date=start,end_date=end,end_reason=reason,origin='Mercado simulado',monthly_wage=1000,renewal=renewal)
  visits=[appointment('a',1,20260101,20260201,'renewed'),appointment('b',1,20260201,20260301,'dismissal',True),appointment('c',2,20260302,20260401,'resignation'),appointment('d',1,20260410)]
  def result(ident,app,club,hg,ag,date,home=True):return dict(match_key=ident,home=club if home else 99,away=99 if home else club,hg=hg,ag=ag,game_date=date,home_appointment=app if home else None,away_appointment=app if not home else None,home_coach='coach' if home else 'other',away_coach='other' if home else 'coach')
  results=[result('1','a',1,2,0,20260102),result('2','b',1,1,1,20260202,False),result('3','c',2,0,1,20260310),result('4','d',1,3,1,20260412)]
  titles=[dict(coach_id='coach',club_id=1,competition_id=7,season=20260101,game_date=20260210,name='Liga')]
  rich=build(person,visits,results,titles,{},clubs,20260420,str);self.assertEqual(3,len(rich['spells']));self.assertEqual(2,rich['clubs']);self.assertEqual(4,rich['total']['games']);self.assertEqual(3,rich['home']['games']);self.assertEqual(1,rich['away']['games']);self.assertEqual(1,len(rich['titles']));self.assertEqual(7,rich['titles'][0]['competition']);self.assertEqual(2,rich['spells'][-1]['total']['games']);self.assertEqual(1,rich['spells'][-1]['titles']);self.assertEqual(1,rich['spells'][0]['total']['games']);self.assertEqual(dict(all='VEDV',home='VDV',away='E'),rich['recent'])
 def test_reference_metric_notes_use_real_games_and_do_not_divide_by_zero(self):
  from model import visual_data
  from engine import score
  p=dict(career=dict(total=score([(2,1),(1,1),(0,2),(2,0)]),home=score([(2,1),(1,1)]),away=score([(0,2),(2,0)]),spells=[],recent=dict(all='VEDV',home='VE',away='DV')),style='Equilibrado',secondaryStyle='',formation='4-3-3')
  data=visual_data(p);self.assertEqual('50,0%',data[1]);self.assertEqual('25,0%',data[2]);self.assertEqual('1,2 por jogo',data[4]);self.assertEqual('profile_pitch_4_3_3',data[26]);p['career']['total']=score([]);self.assertEqual('—',visual_data(p)[1])

if __name__=='__main__':unittest.main()
