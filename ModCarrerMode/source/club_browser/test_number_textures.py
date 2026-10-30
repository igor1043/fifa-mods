import struct,unittest
from unittest.mock import patch
import numpy as np
import kit_personalization as k
from native_assets import decode

class Font:
 def __init__(self,raw):self.raw=raw
 def names(self):return [(k.TEXTURE,'digit_'+str(i)) for i in range(10)]
 def get(self,typ):return [self.raw]*10

def record(kind,w,h,pixels,pitch=None):
 row=(w+3)//4*(8 if kind==0 else 16) if kind<3 else w*{3:4,4:1,5:2}.get(kind,4)
 rows=(h+3)//4 if kind<3 else h
 raw=bytearray(32);raw[5]=kind;struct.pack_into('<HH',raw,8,w,h)
 struct.pack_into('<4I',raw,16,pitch or row,rows,len(pixels),0)
 return bytes(raw)+pixels

class NativeNumberTextures(unittest.TestCase):
 def test_big_endian_rx3_metadata_preserves_the_actual_digit_pixels(self):
  little=record(3,2,1,b'\x03\x02\x01\xff\x06\x05\x04\x80')
  big=bytearray(little);struct.pack_into('>I',big,0,len(big))
  struct.pack_into('>4H',big,8,2,1,1,1);struct.pack_into('>4I',big,16,8,1,8,0)
  label=b'digit_0\0';names=struct.pack('>4I',32+len(label),1,0,0)+struct.pack('>II',k.TEXTURE,len(label))+label
  offset=48;raw=b'RX3b'+struct.pack('>3I',4,offset+len(big)+len(names),2)
  raw+=struct.pack('>4I',k.TEXTURE,offset,len(big),0)+struct.pack('>4I',k.NAME,offset+len(big),len(names),0)+big+names
  parsed=k.number_rx3(bytes(raw));self.assertEqual(parsed.names(),[(k.TEXTURE,'digit_0')])
  self.assertEqual(list(decode(k.texture_record(parsed,'digit_0')).getdata()),[(1,2,3,255),(4,5,6,128)])
  self.assertEqual(k.texture_record(parsed,'digit_0')[3],k.texture_record(Font(little),'digit_0')[3])
 def test_bgra_rows_keep_color_alpha_and_ignore_padding_and_lower_mips(self):
  pixels=bytes([3,2,1,255, 30,20,10,128])+b'PAD!'+bytes([9,8,7,64, 60,50,40,0])+b'PAD!'
  raw=record(3,2,2,pixels,12);font=Font(raw+b'lower mip ignored')
  result=k.texture_record(font,'digit_7');image=decode(result)
  self.assertEqual(list(image.getdata()),[(1,2,3,255),(10,20,30,128),(7,8,9,64),(40,50,60,0)])
  self.assertEqual(font.raw,raw+b'lower mip ignored');self.assertEqual(result[:3],(2,2,3))
 def test_compressed_pixels_are_preserved_for_all_dxt_variants(self):
  for kind,size in ((0,8),(1,16),(2,16)):
   pixels=bytes(range(size));font=Font(record(kind,4,4,pixels))
   self.assertEqual(k.texture_record(font,'digit_0'),(4,4,kind,pixels))
 def test_luminance_and_luminance_alpha(self):
  self.assertEqual(list(decode(k.texture_record(Font(record(4,2,1,b'\x00\xff')),'digit_1')).getdata()),[(0,0,0,255),(255,255,255,255)])
  self.assertEqual(list(decode(k.texture_record(Font(record(5,2,1,b'\x40\x00\x80\xff')),'digit_1')).getdata()),[(64,64,64,0),(128,128,128,255)])
 def test_truncation_or_invalid_pitch_is_rejected_before_sampling(self):
  raw=record(3,2,2,bytes(16))
  for bad in (raw[:-1],raw[:16]+struct.pack('<I',1)+raw[20:]):
   with self.assertRaises(ValueError):k.texture_record(Font(bad),'digit_1')
 def test_bad_optional_number_uses_next_native_candidate_without_losing_player(self):
  dtype=np.dtype([('p','<f4',3),('n','<f4',3),('uv','<f4',2),('j','<u2',8),('w','u1',8)])
  v=np.zeros(4,dtype=dtype);v['p']=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]];v['uv']=[[0,0],[1,0],[1,1],[0,1]];v['n']=[0,0,1];v['w'][:,0]=255
  part=dict(asset='data/sceneassets/jersey/jersey_0.rx3',texture=0,v=v,idx=np.array([0,1,2,0,2,3],dtype='<u4'),skinned=True)
  rig=dict(parts=[part],textures=[(1,1,3,b'\xff'*4)])
  good=Font(record(3,1,1,b'\xff'*4));bad=Font(record(99,1,1,b'\xff'*4))
  def read(path):
   if '/kit/' in path:return b'kit'
   if 'specifickitnumbers_' in path:return b'bad'
   if path.endswith('kitnumbers_0_0.rx3'):return b'good'
   raise FileNotFoundError(path)
  def rx(raw):return good if raw==b'good' else bad
  with patch.object(k,'Rx3',side_effect=rx),patch.object(k,'hotspots',return_value={'jersey':{'numberback':(.2,.2,.8,.8)}}):
   out,report=k.personalize(rig,dict(club=1043,position='ATA',league=7,name='Player',number=9),read)
  self.assertTrue(report['number']);self.assertTrue(report['numbers'].endswith('kitnumbers_0_0.rx3'))
  self.assertTrue(report['number_fallbacks']);self.assertEqual(len(rig['parts']),1);self.assertIs(out['parts'][0],part)

if __name__=='__main__':unittest.main(verbosity=2)
