import copy,json,tempfile,unittest
from pathlib import Path
import credit_policy as c
import loans as l
import save_sidecar as sql

def profile(level=1,prestige=20,budget=26_000_000,overall=73):
    return dict(club=1043,level=level,prestige=prestige,base_budget=budget,overall=overall,player_weekly=1_000_000)

class CreditPolicyTests(unittest.TestCase):
    def test_big_club_can_request_100m_lower_divisions_cannot(self):
        self.assertGreaterEqual(c.capacity(profile()),100_000_000)
        self.assertLessEqual(c.capacity(profile(2)),12_000_000)
        self.assertLessEqual(c.capacity(profile(3)),4_000_000)
        self.assertGreater(c.capacity(profile(2)),c.capacity(profile(3)))
        self.assertGreater(c.capacity(profile(1,20)),c.capacity(profile(1,4)))
    def test_bank_choices_are_sorted_and_existing_debt_reduces_facility(self):
        state=l.empty(1043,20260101);a=c.offers(state,profile(2),20260101)
        self.assertGreater(a['banks']['10']['limit'],a['banks']['5']['limit'])
        amounts=[l.AMOUNTS[i] for i in a['banks']['10']['amounts']]
        self.assertEqual(amounts,sorted(amounts));self.assertEqual(amounts[0],100_000)
        state,budget,_=l.borrow(state,request_id='old',club=1043,today=20260101,budget=20_000_000,bank=10,amount=5_000_000,months=24)
        b=c.offers(state,profile(2),20260301)
        self.assertEqual(a['banks']['10']['limit']-b['banks']['10']['limit'],5_000_000)
        with self.assertRaisesRegex(ValueError,'acima do crédito'):
            l.request_loan(state,request_id='over',club=1043,today=20260301,budget=budget,bank=10,amount=10_000_000,months=24,credit=b)
    def test_refused_bank_waits_calendar_month_other_bank_can_accept(self):
        state=l.empty(1043,20260128);credit=c.offers(state,profile(2),20260128)
        state,budget,_=l.request_loan(state,request_id='refused',club=1043,today=20260128,budget=10_000_000,bank=9,amount=1_000_000,months=12,credit=credit,underwriting_roll=0)
        state,budget,_,decision=l.decide_loan(state,club=1043,today=20260131,budget=budget,credit=credit)
        self.assertFalse(decision['approved']);self.assertEqual(budget,10_000_000)
        state=json.loads(json.dumps(state));credit=c.offers(state,profile(2),20260201)
        self.assertEqual(credit['banks']['9']['retry_date'],20260228)
        with self.assertRaisesRegex(ValueError,'28/02'):
            l.request_loan(state,request_id='same',club=1043,today=20260201,budget=budget,bank=9,amount=1_000_000,months=12,credit=credit)
        before=l.underwriting(l.empty(1043,20260201),'other',budget,7,1_000_000,12,9999,credit,20260201)
        state,_,_=l.request_loan(state,request_id='other',club=1043,today=20260201,budget=budget,bank=7,amount=1_000_000,months=12,credit=credit,underwriting_roll=9999)
        self.assertGreater(state['application']['underwriting']['decline_bps'],before['decline_bps'])
        state,budget,_,decision=l.decide_loan(state,club=1043,today=20260203,budget=budget,credit=credit)
        self.assertTrue(decision['approved']);self.assertEqual(budget,11_000_000)
    def test_four_contracts_with_two_month_spacing_and_annual_limit(self):
        state=l.empty(1043,20260101);budget=20_000_000
        for i,today in enumerate((20260101,20260301,20260501,20260701)):
            state,budget,_=l.borrow(state,request_id=str(i),club=1043,today=today,budget=budget,bank=9,amount=1_000_000,months=48)
            with self.assertRaisesRegex(ValueError,'dois meses|quatro empréstimos'):
                l.borrow(state,request_id='early',club=1043,today=today+1,budget=budget,bank=9,amount=1_000_000,months=48)
        self.assertEqual(len(state['contracts']),4)
        with self.assertRaisesRegex(ValueError,'quatro empréstimos ativos'):
            l.borrow(state,request_id='fifth',club=1043,today=20260901,budget=budget,bank=9,amount=1_000_000,months=48)
        for contract in list(state['contracts']):
            state,budget,_=l.pay(state,request_id='pay'+contract['id'],contract_id=contract['id'],club=1043,today=20260901,budget=budget,settle=True)
        with self.assertRaisesRegex(ValueError,'quatro empréstimos no ano'):
            l.borrow(state,request_id='fifth-paid',club=1043,today=20260901,budget=budget,bank=9,amount=1_000_000,months=12)
    def test_offer_rate_increases_with_utilization_and_is_frozen(self):
        state=l.empty(1043,20260101);credit=c.offers(state,profile(2),20260101)
        self.assertGreater(c.quote(credit,10,10_000_000,24)['rate_bps'],c.quote(credit,10,1_000_000,24)['rate_bps'])
        state,_,_=l.request_loan(state,request_id='frozen',club=1043,today=20260101,budget=20_000_000,bank=10,amount=1_000_000,months=24,credit=credit,underwriting_roll=9999)
        quoted=copy.deepcopy(state['application']['quote'])
        state,_,_,decision=l.decide_loan(state,club=1043,today=20260103,budget=20_000_000,credit=credit)
        self.assertTrue(decision['approved']);self.assertEqual(state['contracts'][0]['total'],quoted['total'])
    def test_sql_custom_policy_survives_and_native_save_stays_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            save=Path(t)/'DATA';save.write_bytes(b'native')
            policy,banks=sql.credit_rules(save)
            with sql.connection(save) as db:
                db.execute("UPDATE credit_rules SET value=6000000 WHERE key='tier_2_cap'")
            self.assertEqual(sql.credit_rules(save)[0]['tier_2_cap'],6_000_000)
            self.assertEqual(save.read_bytes(),b'native')

if __name__=='__main__':unittest.main()
