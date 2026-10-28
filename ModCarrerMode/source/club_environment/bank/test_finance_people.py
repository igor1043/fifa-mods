import unittest
from finance_people import payroll_rows,club_transfers,debts
from loans import BANKS,empty,borrow

class FinancePeopleTests(unittest.TestCase):
 def test_payroll_uses_only_active_members_and_current_wage(self):
  roster=[dict(id=i,name='Jogador '+str(i),position='ATA',overall=80) for i in (10,20,30)]
  rows=payroll_rows(roster,[dict(playerid=10,wage=1200,offered_wage=99999),dict(playerid=20,wage=400),dict(playerid=20,wage=500),dict(playerid=99,wage=100000)])
  self.assertEqual({p['id'] for p in rows},{10,20,30})
  self.assertEqual((rows[0]['weekly'],rows[0]['monthly'],rows[0]['annual']),(1200,5200,62400))
  self.assertIsNone(rows[1]['weekly']);self.assertIsNone(rows[2]['weekly'])
 def test_transfers_filter_club_season_and_future_without_counting_cash(self):
  base=dict(id=1,playerId=10,playerName='Jogador',date='2026-05-11',fee=1234,loan=False,
   **{'from':dict(id=2,name='Origem'),'to':dict(id=3,name='Destino')})
  payload=dict(transfers=[base,dict(base,id=2,date='2025-12-31'),dict(base,id=3,date='2026-06-01')])
  self.assertEqual(club_transfers(payload,99,20260101,20260511),[])
  result=club_transfers(payload,3,20260101,20260511)
  self.assertEqual(len(result),1);self.assertEqual(result[0]['direction'],'in');self.assertEqual(result[0]['other']['id'],2)
  self.assertEqual(club_transfers(payload,2,20260101,20260511)[0]['direction'],'out')
 def test_debt_summary_uses_remaining_installments_without_changing_ledger(self):
  state,_,_=borrow(empty(55,20260511),request_id='test',club=55,today=20260511,budget=10_000_000,bank=0,amount=1_000_000,months=12)
  contract=state['contracts'][0];contract['paid']=1
  result=debts([contract],BANKS)[0]
  self.assertEqual(result['balance'],sum(p['amount'] for p in contract['payments'][1:]))
  self.assertEqual(result['next_date'],contract['payments'][1]['date'])
  self.assertEqual((contract['paid'],result['paid'],result['total']),(1,1,12))

if __name__=='__main__':unittest.main()
