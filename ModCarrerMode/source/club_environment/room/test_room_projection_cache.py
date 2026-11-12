import tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
import room_projection_r52 as p

class ProjectionCache(unittest.TestCase):
    def test_reuses_same_revision_but_invalidates_changed_save_and_other_career(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data/db').mkdir(parents=True)
            db=root/'data/db/fifa_ng_db.db';db.write_bytes(b'base')
            meta=root/'meta.xml';meta.write_text('<database/>')
            a=root/'career-a';a.write_bytes(b'save-a');b=root/'career-b';b.write_bytes(b'save-b')
            with patch.object(p,'GAME',root),patch.object(p,'_base_cache',None),patch.object(p,'_saved_cache',None),patch.object(p,'_metadata_cache',None),patch.object(p,'blocks',return_value=[]),patch.object(p,'tables',side_effect=lambda data,*args,**kwargs:{'bytes':data}) as decode:
                first=p.read_table_sets(a,meta);again=p.read_table_sets(a,meta)
                self.assertIs(first[0],again[0]);self.assertEqual(decode.call_count,2)
                old=a.stat().st_mtime_ns;a.write_bytes(b'save-new');os.utime(a,ns=(old+1_000_000,old+1_000_000))
                changed=p.read_table_sets(a,meta);self.assertEqual(changed[0]['bytes'],b'save-new');self.assertEqual(decode.call_count,3)
                other=p.read_table_sets(b,meta);self.assertEqual(other[0]['bytes'],b'save-b');self.assertEqual(decode.call_count,4)
if __name__=='__main__':unittest.main()
