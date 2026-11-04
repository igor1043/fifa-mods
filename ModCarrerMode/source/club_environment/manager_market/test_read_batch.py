import unittest
from unittest.mock import patch
import test_engine

class ReadBatch(test_engine.EngineTest):
 def test_cache_is_invalidated_by_mutation_and_callers_cannot_edit_it(self):
  with self.m.db,self.m.db.read_batch():
   clubs=self.m.rows('clubs');clubs[0]['name']='Editado fora do banco'
   self.assertNotEqual(clubs[0]['name'],self.m.rows('clubs')[0]['name'])
   self.m.db.execute('UPDATE clubs SET name=? WHERE branch=? AND club_id=?',('Nome novo',self.m.branch,clubs[0]['club_id']))
   self.assertEqual('Nome novo',self.m.one('clubs','club_id',clubs[0]['club_id'])['name'])
   self.assertIn('Nome novo',[c['name'] for c in self.m.rows('clubs')])
 def test_rollback_does_not_leave_a_cached_appointment(self):
  coach=self.m.active(club=1)['coach_id']
  with self.assertRaises(ValueError):
   with self.m.db,self.m.db.read_batch():
    self.m.leave(self.m.active(club=1),20260201,'dismissal','Teste')
    self.assertIsNone(self.m.active(club=1));raise ValueError('rollback')
  with self.m.db.read_batch():self.assertEqual(coach,self.m.active(club=1)['coach_id'])
 def test_batch_does_not_reuse_another_career_branch(self):
  original=self.m.branch
  with self.m.db,self.m.db.read_batch():
   self.m.rows('clubs');self.m.branch=self.m.clone(original)
   self.m.db.execute('UPDATE clubs SET name=? WHERE branch=? AND club_id=1',('Outra carreira',self.m.branch))
   self.assertEqual('Outra carreira',self.m.one('clubs','club_id',1)['name'])
   self.m.branch=original;self.assertEqual('Clube 1',self.m.one('clubs','club_id',1)['name'])
 def test_unchanged_user_wage_does_not_invalidate_all_appointments_each_day(self):
  before=self.m.db.versions['appointments']
  self.m.ensure_user(test_engine.context(),20260102)
  self.assertEqual(before,self.m.db.versions['appointments'])
 def test_metadata_is_resynchronised_after_a_failed_transaction(self):
  changed=dict(self.m.one('clubs','club_id',1),name='Nome atualizado');changed.pop('branch')
  c=dict(test_engine.context(),clubs=[changed]);self.m.db.commit()
  with self.assertRaises(ValueError):
   with self.m.db:self.m.sync_clubs(c);raise ValueError('rollback')
  self.assertEqual('Clube 1',self.m.one('clubs','club_id',1)['name'])
  with self.m.db:self.m.sync_clubs(c)
  self.assertEqual('Nome atualizado',self.m.one('clubs','club_id',1)['name'])

if __name__=='__main__':unittest.main()
