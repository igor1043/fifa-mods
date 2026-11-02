import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
import club_finance as f
import save_sidecar as sql
from loans import empty
from test_club_finance import context,match
from finance_report import categories,native_view
from finance_competitions import profiles,enrich


class BalanceTests(unittest.TestCase):
 def test_competition_and_mando_weights_keep_regional_below_national_cup(self):
  club=dict(base_budget=26_000_000,prestige=20,league_budget=15_000_000,league=7)
  profile=context()['competitions'][0];p=f.rules();values={}
  for category in ('league','cup','continental','regional'):
   terms=f.agreement(dict(profile,category=category,importance=80),20260101,20260101,p,club)
   home,_=f.tv_payment(terms,match(),1043);away,_=f.tv_payment(terms,match(home=567,away=1043),1043)
   self.assertGreater(home,away);values[category]=home
  self.assertLess(values['regional'],values['league'])
  self.assertGreater(values['cup'],values['league']);self.assertGreater(values['continental'],values['cup'])

 def test_dynamic_hierarchy_classifies_new_league_cup_and_regional_without_names(self):
  meta={1:dict(asset=7,category='league',parent=10,mode='LEAGUE',importance=80),
        2:dict(asset=999,category='cup',parent=10,mode='CUP',importance=70),
        3:dict(asset=888,category='cup',parent=11,mode='CUP',importance=40)}
  for root,category in ((1,'league'),(2,'cup'),(3,'regional')):
   self.assertEqual(enrich(dict(root=root,name='Outro nome'),meta,7)['category'],category)

 def test_revision_is_prospective_and_repeated_days_cannot_duplicate_debits(self):
  ctx=context();ctx['club_profile']=dict(base_budget=26_000_000,prestige=20)
  s,b,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=50_000_000,context=ctx)
  # Recreate an older saved checkpoint, including its historical contracts.
  book=s['finance'];book['economy_version']=3;book['rules']=dict(f.PREVIOUS_RULES)
  book['settings'].pop('facilities');book['settings_history'][0]['values'].pop('facilities')
  old=next(iter(book['agreements'].values()));old.pop('category');old['rules']=dict(f.PREVIOUS_RULES)
  old['per_match']=123456
  book['commercial']={str(ctx['season']):dict(start=20260511,sponsor_annual=1000,staff_annual=2000)}
  preserved=copy.deepcopy(book)
  ctx['date']=20260531;ctx['fixtures']=[match(day=20260511),match(2,day=20260512)]
  s,after,events=f.apply(s,club=1043,today=20260531,budget=b,context=ctx)
  terms=next(iter(s['finance']['agreements'].values()))
  self.assertEqual(f.match_terms(terms,20260511)['per_match'],123456)
  self.assertEqual(f.match_terms(terms,20260511)['rules'],f.PREVIOUS_RULES)
  self.assertEqual(f.match_terms(terms,20260512)['rules']['match_cost_bps'],6500)
  self.assertTrue(any(e['kind']=='facilities' for e in events))
  self.assertEqual(after-b,f.cash_delta(events))
  again,same,repeated=f.apply(s,club=1043,today=20260531,budget=after,context=ctx)
  self.assertEqual(again,s);self.assertEqual(same,after);self.assertFalse(repeated)
  self.assertEqual(preserved['entries'],[])

 def test_facilities_switch_and_master_switch_prorate_days(self):
  s,b,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=50_000_000,context=context())
  s=f.toggle(s,'facilities',False,20260515)
  s,_,_=f.apply(s,club=1043,today=20260531,budget=b,context=context(20260531))
  row=next(e for e in s['finance']['entries'] if e['kind']=='facilities')
  self.assertEqual(row['enabled_days'],4);self.assertLess(row['amount'],0)
  self.assertEqual(f.SWITCHES[:8],('enabled','tv','tickets','coach','loans','sponsor','staff','match_costs'))

 def test_sql_calibration_preserves_custom_rates_and_native_bytes(self):
  with tempfile.TemporaryDirectory() as folder:
   save=Path(folder)/'DATA';save.write_bytes(b'do not modify native save')
   sql.bank_rows(save)
   with sql.connection(save) as db:
    sql.finance_schema(db);db.execute("INSERT INTO finance_meta VALUES('calibration_v2',2)")
    db.executemany('INSERT INTO finance_rules VALUES(?,?)',f.PREVIOUS_RULES.items())
    db.execute("UPDATE finance_rules SET value=5200 WHERE key='match_cost_bps'")
   p=sql.finance_rules(save)
   self.assertEqual(p['tv_match_bps'],100);self.assertEqual(p['match_cost_bps'],5200)
   self.assertEqual(p['staff_annual_bps'],4000);self.assertEqual(p['facilities_annual_bps'],3000)
   self.assertEqual(sql.finance_rules(save),p)
   self.assertTrue((Path(folder)/'server16_loans.before-finance-v4.sqlite3').is_file())
   self.assertEqual(save.read_bytes(),b'do not modify native save')

 def test_complete_report_keeps_zeros_and_never_adds_principal_to_profit(self):
  view=dict(date=20261201,months=[dict(month=202611,tv=100,loan_credit=1000,loans=-120,interest=-20)],
   transfers=[dict(id=1,date=20260510,direction='out',fee=500,loan=False),dict(id=2,date=20260511,direction='in',fee=200,loan=False)])
  original=copy.deepcopy(view);report=categories(view)
  income={r['key']:r for r in report['revenues']};expense={r['key']:r for r in report['expenses']}
  self.assertEqual(income['transfer']['value'],500);self.assertEqual(expense['transfer']['value'],200)
  self.assertEqual(income['loan']['value'],1000);self.assertEqual(expense['loan']['value'],100)
  self.assertEqual(expense['interest']['value'],20);self.assertEqual(income['sponsor']['value'],0)
  self.assertIsNone(income['prize']['value']);self.assertEqual(view,original)

 def test_unknown_native_journal_is_not_invented_from_balance_or_trophies(self):
  def rows(*args):raise AssertionError('Current contracts are not historical payments')
  native=native_view(rows,club=1043,season=20260101,today=20261201)
  self.assertIsNone(native['prizes']);self.assertIsNone(native['bonuses'])


if __name__=='__main__':unittest.main()
