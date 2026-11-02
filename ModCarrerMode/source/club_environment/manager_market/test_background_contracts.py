import unittest,copy
import test_screen
from worker import contract_signature

class ContractSignatureTest(unittest.TestCase):
 def test_only_football_contract_evidence_restarts_work(self):
  o=dict(signature=('career','20260814'),profile=dict(context_epoch=2));token=('read','1','slot/DATA');live=dict(revision='same-leagues')
  snap=dict(nodes=[[2,1],[1,0]],fixtures=[[2,1,0],[1,1,0]],standings=[[2,1],[1,1]],stats=[[100,30]],standingGoals={'1':[0,0,0,0]})
  first=contract_signature(o,snap,token,live,[[2,1],[1,1]])
  reordered=copy.deepcopy(snap)
  for key in ('nodes','fixtures','standings'):reordered[key].reverse()
  reordered['stats']=[[100,60]]
  self.assertEqual(first,contract_signature(o,reordered,token,live,[[1,1],[2,1]]))
  changed=copy.deepcopy(snap);changed['fixtures'][0][-1]=1
  self.assertNotEqual(first,contract_signature(o,changed,token,live,[[2,1],[1,1]]))
  self.assertNotEqual(first,contract_signature(o,snap,('read','2','slot/DATA'),live,[[2,1],[1,1]]))
  self.assertNotEqual(first,contract_signature(dict(o,profile=dict(context_epoch=3)),snap,token,live,[[2,1],[1,1]]))

if __name__=='__main__':unittest.main()
