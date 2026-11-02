import unittest
import finance_ui as ui
from test_club_finance_ui import view,open_finance


class AnnualUI(unittest.TestCase):
 def test_year_navigation_is_local_and_back_restores_history_then_current_view(self):
  v=view();v['date']=20270120
  v['annual_history']=[dict(year=y,income=1000+y,expenses=500,result=500+y,closing_budget=10000,last_date=y*10000+1231,months=[]) for y in (2027,2026)]
  pages=ui.scenes(v);keys={p['key']:i for i,p in enumerate(pages)}
  vm,screen,calls=open_finance(v);overview=next(p for p in pages if p['key']=='overview');index=next(i for i,b in enumerate(overview['actions']) if b['target']=='history')
  screen.set('focus',index);vm.invoke(screen.get('Select'),screen);self.assertEqual(keys['history'],screen.get('page'))
  vm.invoke(screen.get('Go'),screen,[keys['year:2026']]);vm.invoke(screen.get('Back'),screen);self.assertEqual(keys['history'],screen.get('page'))
  vm.invoke(screen.get('Back'),screen);self.assertEqual(keys['overview'],screen.get('page'))
  self.assertFalse(any(n=='SendSystemEvent' and len(a)>1 and a[1]=='Server16SubmitBank' for n,a in calls))
  for p in pages:
   for b in p['actions']:
    if not b['target'].startswith('toggle:'):self.assertIn(b['target'],keys)

if __name__=='__main__':unittest.main()
