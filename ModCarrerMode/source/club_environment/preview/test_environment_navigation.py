"""Exercise the deployed entry/exit flows and their rendering layers."""
import json,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]

class EnvironmentNavigationTests(unittest.TestCase):
 def flow(self,name):
  return json.loads((ROOT/'data/ui/nav/careermode'/name).read_text(encoding='utf8'))

 def enter(self,flow):
  state=next(s for s in flow['states'] if s['name']==flow['initial']['targets'][0])
  layers={};controllers=set();models=set()
  for action,args in state['onEnter']:
   if action=='loadView':layers[args[0]]=args[1:]
   if action=='loadScreenController':controllers.add(args[0])
   if action=='loadViewModel':models.add(args[0])
  return state,layers,controllers,models

 def test_room_entry_never_puts_a_photograph_over_the_native_3d_scene(self):
  state,layers,controllers,models=self.enter(self.flow('server16dressingroomflow.nav'))
  self.assertEqual(layers,{'screen':['game/screens/career/server16/DressingRoom']})
  self.assertEqual(controllers,{'Calendar'})
  self.assertNotIn(['unloadView',['background']],state['onExit'])
  self.check_back(state)

 def test_next_match_enters_populated_custom_card_without_waiting_for_an_external_event(self):
  state,layers,controllers,models=self.enter(self.flow('server16matchpreviewflow.nav'))
  self.assertEqual(layers['screen'],['game/screens/career/server16/MatchPreview'])
  self.assertEqual(controllers,{'Calendar'});self.assertEqual(models,{'StartingXIViewModel'})
  self.assertEqual({t['event'] for t in state['transitions']},{'Back','back'})
  self.assertIn(['unloadView',['screen','game/screens/career/server16/MatchPreview']],state['onExit'])
  self.check_back(state)

 def check_back(self,state):
  for event in ('Back','back'):
   transition=next(t for t in state['transitions'] if t['event']==event)
   self.assertEqual(transition['targets'],['Back'])
   self.assertEqual(transition['actions'],[['executeCMAction',['ReturnToHubFromCalendar']]])

if __name__=='__main__':unittest.main()
