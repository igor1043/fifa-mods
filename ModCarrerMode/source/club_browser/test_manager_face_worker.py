"""Exercise the real creation worker using installed assets and isolated output."""
from pathlib import Path
import os,tempfile,unittest,json,shutil
from unittest.mock import patch
import manager_face_worker as worker
import portable_paths
from manager_market.model_assets import catalog,installed
from model_exporter import Exporter
from coach_animation import CLIPS,select as select_native_idle

class CreationWorker(unittest.TestCase):
 def test_preview_does_not_need_or_read_a_career(self):
  real=portable_paths.GAME
  key,row=next((key,row) for key,row in catalog(real).items() if row['name']=='Tite' and installed(real,row))
  with tempfile.TemporaryDirectory(prefix='face worker ') as folder:
   game=Path(folder);runtime=game/'ModCarrerMode/runtime';requests=runtime/'club_browser/7';requests.mkdir(parents=True)
   draft=runtime/'user_manager/draft.tsv';draft.parent.mkdir();draft.write_text('pid=7\nactive=1\n')
   req=dict(schema=1,pid=7,seq=10,club=row['assetId'],kind='manager_face',coach=key)
   (requests/'request.tsv').write_text(''.join(f'{k}={v}\n' for k,v in req.items()))
   relative=Path('ModCarrerMode/tools/club_browser/generate_lineup.exe');(game/relative).parent.mkdir(parents=True);shutil.copy2(real/relative,game/relative)
   for clip in CLIPS:
    animation=game/'ModCarrerMode/data/club_browser/animations'/clip;animation.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(real/'ModCarrerMode/data/club_browser/animations'/clip,animation)
   native=Exporter()
   exported=[]
   class IsolatedExporter:
    def run(self,tool,unused,fixture,target,**kwargs):
     exported.append(1);return native.run(tool,real,fixture,target,**kwargs)
   class NoCareerMemory:
    def __getattr__(self,key):raise AssertionError('Creation must not read career memory')
   publish_directory=worker.publish_directory
   def empty_remnant(source,target):
    # Both the prepared cache and the per-session publication can retain an
    # empty directory after cleanup. Exercise the real Windows rename path.
    target.mkdir(parents=True,exist_ok=True);return publish_directory(source,target)
   class DesiredIdle:
    def choice(self,choices):
     if clip not in choices:raise AssertionError('Requested idle is unavailable or repeated')
     return clip
   def choose_idle(*args,**kwargs):return select_native_idle(*args,rng=DesiredIdle(),**kwargs)
   try:
    hashes=set();measurements=[]
    with patch.object(worker,'catalog',return_value={key:row}),patch.object(worker,'installed',return_value=True),patch.object(worker,'ensure'),patch.object(worker,'publish_directory',side_effect=empty_remnant),patch.object(worker,'select_animation',side_effect=choose_idle):
     with patch.object(worker,'_prepared_clips',return_value=()):
      for i,clip in enumerate(CLIPS):
       req['seq']=10+i;(requests/'request.tsv').write_text(''.join(f'{k}={v}\n' for k,v in req.items()))
       self.assertTrue(worker.generate(game,requests,req,NoCareerMemory(),IsolatedExporter()))
       status=dict(line.split('=',1) for line in (requests/'status.tsv').read_text().splitlines())
       self.assertEqual(status['animation'],Path(clip).stem);self.assertEqual(status['actor'],'1');self.assertEqual(len(status['bindings'].split(',')),96)
       target=game/'data/sceneassets/server16_club_xi/7'/status['hash'];self.assertTrue((target/'animation.bin').is_file());hashes.add(status['hash'])
       measurements.append(json.loads((requests/'face-timings.json').read_text()))
     clip=CLIPS[0];req['seq']+=1;(requests/'request.tsv').write_text(''.join(f'{k}={v}\n' for k,v in req.items()))
     with patch.object(worker,'bake',side_effect=AssertionError('A ready animation must be reused')):
      self.assertTrue(worker.generate(game,requests,req,NoCareerMemory(),IsolatedExporter()))
     measurements.append(json.loads((requests/'face-timings.json').read_text()))
    self.assertEqual(len(hashes),len(CLIPS))
    self.assertEqual(len(exported),1,'Changing only idle must not reexport the coach')
    self.assertTrue(measurements[1]['model_cache_hit']);self.assertTrue(measurements[-1]['animation_cache_hit'])
    print('FACE_TIMINGS',json.dumps(measurements))
   finally:native.close()
   status=dict(line.split('=',1) for line in (requests/'status.tsv').read_text().splitlines())
   self.assertEqual(status['actor'],'1');self.assertEqual(status['coach_id'],key);self.assertEqual(status['career'],'0');self.assertEqual(status['kind'],'manager_face')
   self.assertEqual(len(status['bindings'].split(',')),96)
   target=game/'data/sceneassets/server16_club_xi/7'/status['hash'];self.assertTrue((target/'animation.bin').is_file())
   draft.write_text('pid=7\nactive=0\n')
   with patch.object(worker,'catalog',return_value={key:row}),patch.object(worker,'installed',return_value=True):
    self.assertTrue(worker.generate(game,requests,req,NoCareerMemory(),None))
   closed=dict(line.split('=',1) for line in (requests/'status.tsv').read_text().splitlines());self.assertEqual(closed['actor'],'0')

if __name__=='__main__':unittest.main()
