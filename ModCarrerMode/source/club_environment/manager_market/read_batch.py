"""Transaction-local read reuse; every SQL mutation invalidates its table.

Never shared across threads/connections, careers, transactions or rollbacks.
The database remains the source of truth; cached dictionaries are not writable
state and callers always receive their own copies.
"""
from collections import OrderedDict
from contextlib import contextmanager
import re
import sqlite3

MUTATION=re.compile(r'^\s*(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|UPDATE(?:\s+OR\s+\w+)?|DELETE\s+FROM)\s+["`\[]?(\w+)',re.I)

class Connection(sqlite3.Connection):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.read_depth=0;self.read_cache=OrderedDict();self.versions={};self.campaign_state=None;self.active_index=None
 def invalidate_all(self):
  self.read_cache.clear();self.campaign_state=None;self.active_index=None
  for table in self.versions:self.versions[table]+=1
 def invalidate(self,sql,changed):
  if not changed:return
  match=MUTATION.match(sql)
  if match:
   table=match[1].lower();self.versions[table]=self.versions.get(table,0)+1
  else:self.invalidate_all()
 def execute(self,sql,parameters=()):
  before=self.total_changes
  try:return super().execute(sql,parameters)
  finally:self.invalidate(sql,self.total_changes!=before)
 def executemany(self,sql,parameters):
  before=self.total_changes
  try:return super().executemany(sql,parameters)
  finally:self.invalidate(sql,self.total_changes!=before)
 def executescript(self,sql):
  self.invalidate_all();return super().executescript(sql)
 def rollback(self):
  self.invalidate_all();return super().rollback()
 def __exit__(self,*args):
  try:return super().__exit__(*args)
  finally:
   if args[0] is not None:self.invalidate_all()
   else:self.read_cache.clear();self.campaign_state=None;self.active_index=None
 @contextmanager
 def read_batch(self):
  if not self.read_depth:self.read_cache.clear();self.campaign_state=None;self.active_index=None
  self.read_depth+=1
  try:yield
  finally:
   self.read_depth-=1
   if not self.read_depth:self.read_cache.clear();self.campaign_state=None;self.active_index=None
 def rows(self,branch,table,where,args):
  if where:return [dict(row) for row in super().execute('SELECT * FROM '+table+' WHERE branch=? AND '+where,(branch,*args))]
  key=(branch,table,where,args);version=self.versions.get(table,0)
  cached=self.read_cache.get(key) if self.read_depth else None
  if cached is None or cached[0]!=version:
   rows=[dict(row) for row in super().execute('SELECT * FROM '+table+' WHERE branch=?'+(' AND '+where if where else ''),(branch,*args))]
   if not self.read_depth:return rows
   self.read_cache[key]=(version,rows);self.read_cache.move_to_end(key)
   while len(self.read_cache)>256:self.read_cache.popitem(last=False)
  else:rows=cached[1]
  return [dict(row) for row in rows]
