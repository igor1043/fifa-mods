import json
from pathlib import Path
import tempfile
import unittest
from career_publication import read


class Publication(unittest.TestCase):
 def test_every_loaded_save_has_its_own_process_context_and_file_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);p=game/'ModCarrerMode/runtime/career_fce_snapshot.json';p.parent.mkdir(parents=True)
   for club,pid,epoch,slot in ((11,123,2,'A'),(98765,123,3,'B'),(42,456,1,'C')):
    save=game/slot/'DATA';save.parent.mkdir();save.write_bytes(slot.encode());st=save.stat()
    saved=dict(path=str(save),pid=pid,process_created_100ns=pid*1000)
    value=dict(schema=3,pid=pid,processCreated100ns=pid*1000,date=20261201,savePath=str(save),saveSize=st.st_size,saveWriteTime100ns=st.st_mtime_ns//100+116444736000000000,fceContextEpoch=epoch,club=club,nodes=[],standings=[],fixtures=[],stats=[])
    p.write_text(json.dumps(value));self.assertIsNotNone(read(game,saved,20261201,epoch=epoch,club=club))
    for wrong in (dict(saved,pid=pid+1),dict(saved,process_created_100ns=0),dict(saved,path=str(game/'OTHER/DATA'))):self.assertIsNone(read(game,wrong,20261201,epoch=epoch,club=club))
    self.assertIsNone(read(game,saved,20261101,epoch=epoch,club=club));self.assertIsNone(read(game,saved,20261201,epoch=epoch+1,club=club));self.assertIsNone(read(game,saved,20261201,epoch=epoch,club=club+1))

if __name__=='__main__':unittest.main()
