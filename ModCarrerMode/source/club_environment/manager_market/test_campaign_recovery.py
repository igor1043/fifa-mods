import tempfile
import unittest
from pathlib import Path
from test_engine import catalog, context, matches
from engine import Market
from campaign_recovery import recover


class Recovery(unittest.TestCase):
 def test_empty_old_reader_branch_replays_once_and_discards_the_abandoned_branch(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'catalog.sqlite3');m=Market(root/'world.sqlite3',root/'catalog.sqlite3')
   try:
    m.open_save('A','DATA',context());m.advance(context(20260401));old=m.branch
    c=dict(context(20260401,matches(20)),digest='A',saved_date=20260101,coverage=dict(native_bound=True))
    r=recover(m,c,'DATA');self.assertEqual(old,r['previous_branch']);self.assertNotEqual(old,m.branch)
    m.advance(c);self.assertEqual(20,len(m.rows('results')));self.assertIsNone(recover(m,c,'DATA'))
    self.assertIsNone(m.db.execute('SELECT id FROM branches WHERE id=?',(old,)).fetchone())
   finally:m.close()
 def test_real_decisions_and_other_save_are_never_rewound(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'catalog.sqlite3');m=Market(root/'world.sqlite3',root/'catalog.sqlite3')
   try:
    m.open_save('A','DATA',context());m.advance(context(20260401));branch=m.branch
    c=dict(context(20260401,matches(20)),digest='B',saved_date=20260101,coverage=dict(native_bound=True))
    self.assertIsNone(recover(m,c,'OTHER'));c['digest']='A'
    m.leave(m.active(club=1),20260401,'dismissal','real decision')
    self.assertIsNone(recover(m,c,'DATA'));self.assertEqual(branch,m.branch)
   finally:m.close()

if __name__=='__main__':unittest.main()
