import tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch
import test_screen
from test_screen import GAME,load_data
from test_engine import catalog,context
from engine import Market
from model import project
from screen import FULL,waiting,scenes_for,script_factory,stars
from PIL import Image
import native_screen
from formats import AptFile,BigFile
from native_review_vm import open_native

class LoadingTest(unittest.TestCase):
 def test_portrait_embedding_fits_largest_placement_without_mutating_sources(self):
  import screen
  source=Image.new('RGBA',(256,256),'red');before=source.tobytes();assets={'head_123':source,'card':Image.new('RGBA',(656,180),'white')};captured={}
  def build(game,path,scenes,art,**kwargs):captured.update(art);return dict(bytes=1)
  with tempfile.TemporaryDirectory() as temp,patch.object(screen,'assets_for',return_value=assets),patch.object(screen,'scenes_for',return_value=[]),patch.object(screen.asset_cache,'revision',return_value='new'),patch.object(screen.native,'build',side_effect=build):
   screen.build(Path(temp),Path(temp)/'test.big',screen.waiting())
  self.assertEqual((204,204),captured['head_123'].size)
  self.assertGreaterEqual(captured['head_123'].width,202)
  self.assertEqual((256,256),source.size);self.assertEqual(before,source.tobytes())
  self.assertEqual((656,180),captured['card'].size)

 def test_static_template_reuses_art_with_current_career_data_and_rejects_damage(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'catalog.sqlite3');market=Market(root/'world.sqlite3',root/'catalog.sqlite3');market.open_save('A','DATA',context());model=project(market);market.close()
   assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
   scenes=scenes_for(model,assets);template=root/'template.big'
   native_screen.build(GAME,root/'first.big',scenes,assets,script_factory=script_factory(model,assets),full_name=FULL,catalogue_groups=True,template_cache=template)
   changed=copy.deepcopy(model);changed['date']=20260202;changed['clubName']='Clube atual';changed['people'][changed['clubRows'][0][7]]['overview'][0]=42
   with patch.object(native_screen,'texture_writer',side_effect=AssertionError('Template re-encoded geometry')):
    result=native_screen.build_from_template(template,root/'new.big',script_factory=script_factory(changed,{}),full_name=FULL)
   self.assertTrue(result['template_cached']);vm,state,_,_=open_native(root/'new.big',full=FULL);load_data(vm,state)
   self.assertIn('02/02/2026',state.get('scene0').get('careerMeta').get('text'));self.assertIn('Clube atual',state.get('scene0').get('careerMeta').get('text'))
   vm.invoke(state.get('Command'),state,(40,));self.assertEqual('42',str(state.get('scene1').get('metric0').get('text')));self.assertEqual([],vm.errors)
   template.write_bytes(b'broken')
   with self.assertRaisesRegex(ValueError,'incompleto'):native_screen.build_from_template(template,root/'bad.big',script_factory=script_factory(changed,{}),full_name=FULL)
 def test_large_art_catalogue_uses_bounded_frames_and_resolves_original_names(self):
  with tempfile.TemporaryDirectory() as tmp:
   model=waiting();assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
   scenes=scenes_for(model,assets)
   scenes[1]['nodes'] += [dict(type='image',asset='head_NOTFOUND_DEFAULT',name='catalogue'+str(i),x=0,y=0,w=16,h=16) for i in range(10001)]
   path=Path(tmp)/'catalogue.big';native_screen.build(GAME,path,scenes,assets,script_factory=script_factory(model,assets),full_name=FULL,catalogue_groups=True)
   apt=AptFile(BigFile(path));frames=[f for c in apt.characters.values() for f in getattr(c,'frames',[])]
   self.assertLess(max(map(len,frames)),10000)
   vm,state,_,_=open_native(path,full=FULL);load_data(vm,state)
   clip=vm.invoke(state.get('FindArtwork'),state,(state.get('scene1'),'catalogue10000'))
   self.assertIsNotNone(clip);vm.invoke(state.get('Reveal'),state,(clip,15,25))
   self.assertEqual(100,clip.get('_alpha'));self.assertEqual(15,clip.get('_x'));self.assertEqual([],vm.errors)
 def test_warm_dds_cache_avoids_encoding_and_repairs_corrupt_entries(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);model=waiting();assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
   def build(name):
    artwork=dict(assets);scenes=scenes_for(model,artwork)
    return native_screen.build(GAME,root/name,scenes,artwork,script_factory=script_factory(model,artwork),full_name=FULL,texture_cache=root/'cache')
   build('cold.big');save=Image.Image.save
   def no_dds(image,fp,*args,**kwargs):
    if kwargs.get('format')=='DDS':raise AssertionError('Warm cache re-encoded a texture')
    return save(image,fp,*args,**kwargs)
   with patch.object(Image.Image,'save',no_dds):build('warm.big')
   self.assertEqual((root/'cold.big').read_bytes(),(root/'warm.big').read_bytes())
   item=next((root/'cache').glob('*.dds'));item.write_bytes(b'broken');build('repaired.big');self.assertEqual(b'DDS ',item.read_bytes()[:4])

if __name__=='__main__':unittest.main()
