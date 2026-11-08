"""Buffer safety regressions for supplied native manager atlases."""
from pathlib import Path
import importlib.util,io,struct,unittest
from PIL import Image
spec=importlib.util.spec_from_file_location('native_import',Path(__file__).with_name('Import-NativeManagerBatch.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def block(w,h):
 out=io.BytesIO();Image.new('RGBA',(w,h),(80,120,160,255)).save(out,format='DDS',pixel_format='DXT5');return out.getvalue()[128:]

def payload(broken=False):
 header=bytearray(16);header[5]=2;struct.pack_into('<4H',header,8,12,12,1,2);first=block(12,12);last=block(6,6)
 if broken:last=last[:36];pitch,rows=24,1
 else:pitch,rows=32,2
 result=header+struct.pack('<4I',48,3,len(first),0)+first+struct.pack('<4I',pitch,rows,len(last),0)+last;result+=bytes((-len(result))%16);struct.pack_into('<I',result,0,len(result));return bytes(result)

class NativeImportTest(unittest.TestCase):
 def test_rebuilds_incomplete_last_block_without_changing_base(self):
  source=payload(True);out,count=module.repair_mips(source);self.assertEqual(1,count);self.assertEqual(source[16:176],out[16:176]);self.assertEqual((32,2,64,0),struct.unpack_from('<4I',out,176));self.assertEqual(len(out),struct.unpack_from('<I',out)[0])
 def test_valid_compressed_mips_remain_byte_for_byte(self):
  source=payload();out,count=module.repair_mips(source);self.assertEqual(0,count);self.assertEqual(source,out)
 def test_bad_base_mip_is_rejected_instead_of_inventing_a_texture(self):
  source=bytearray(payload());struct.pack_into('<I',source,16,47)
  with self.assertRaises(ValueError):module.repair_mips(source)
 def test_invalid_dimensions_are_rejected_before_allocation(self):
  source=bytearray(payload());struct.pack_into('<H',source,8,65535)
  with self.assertRaises(ValueError):module.repair_mips(source)

if __name__=='__main__':unittest.main()
