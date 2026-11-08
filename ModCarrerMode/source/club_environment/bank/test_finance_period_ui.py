import unittest
import finance_ui as ui
from test_club_finance_ui import view,open_finance
from finance_report import composition

class PeriodUI(unittest.TestCase):
 def fixture(self):
  v=view();v.update(date=20260725,months=[dict(month=202607,tv=100,tickets=300,members=250,sponsor=200,coach=-150),dict(month=202606,tv=400,tickets=100,sponsor=100,members=20,staff=-200)])
  return v
 def test_donuts_have_distinct_images_per_month_and_cover_all_categories(self):
  scenes=ui.scenes(self.fixture());july=next(p for p in scenes if p['key']=='receipts:month:202607');june=next(p for p in scenes if p['key']=='receipts:month:202606')
  a=next(n['asset'] for n in july['nodes'] if n.get('asset','').startswith('periodDonut'))
  b=next(n['asset'] for n in june['nodes'] if n.get('asset','').startswith('periodDonut'))
  self.assertNotEqual(a,b);self.assertNotEqual(july['assets'][a].tobytes(),june['assets'][b].tobytes())
  self.assertIn('Sócio-torcedor',{n.get('text') for n in july['nodes']})
  self.assertEqual(sum(r['value'] for r in composition(self.fixture(),'receipts',202607)),850)
 def test_month_navigation_is_local_and_emits_no_financial_transaction(self):
  v=self.fixture();scenes=ui.scenes(v);keys={s['key']:i for i,s in enumerate(scenes)}
  vm,s,calls=open_finance(v);vm.invoke(s.get('Go'),s,[keys['receipts:month:202607']])
  vm.invoke(s.get('LocalEventHandler'),s,[12,None]);self.assertEqual(s.get('page'),keys['receipts:month:202606'])
  vm.invoke(s.get('LocalEventHandler'),s,[11,None]);self.assertEqual(s.get('page'),keys['receipts:month:202607'])
  self.assertFalse(any(n=='SendSystemEvent' and a[1]=='Server16SubmitBank' for n,a in calls))
 def test_all_actions_are_in_content_area_and_targets_exist(self):
  scenes=ui.scenes(self.fixture());keys={p['key'] for p in scenes}
  for p in scenes:
   for a in p['actions']:
    self.assertLessEqual(a['y']+a['h'],870,(p['key'],a))
    if not a['target'].startswith(('toggle:','leave')):self.assertIn(a['target'],keys,(p['key'],a['target']))

if __name__=='__main__':unittest.main()
