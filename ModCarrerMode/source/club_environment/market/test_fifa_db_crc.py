import struct,unittest
from fifa_db_crc import crc32,regions,issues,update_tables

def fixture():
 # Two tables, the first with deliberately unaligned payload + 5 padding
 # bytes. The physical next-table pointer defines the CRC location.
 data=bytearray(156);data[:4]=b'DB\0\x08';struct.pack_into('<I',data,8,len(data));struct.pack_into('<I',data,16,2)
 struct.pack_into('<4sI4sI',data,24,b'One1',0,b'Two2',56)
 for start in (44,100):
  struct.pack_into('<I',data,start+4,3);struct.pack_into('<HH',data,start+16,1,1)
 data[80:83]=b'one';data[136:139]=b'two'
 for r in regions(data):struct.pack_into('<I',data,r.checksum,crc32(memoryview(data)[r.start:r.end]))
 return bytes(data)

class FifaDbCrcTests(unittest.TestCase):
 def test_known_polynomial_and_physical_padding(self):
  self.assertEqual(crc32(b'123456789'),0x0376e6e7)
  data=fixture();self.assertEqual(issues(data),[])
  self.assertEqual(next(r.checksum for r in regions(data) if r.table=='One1' and r.kind=='data'),96)
 def test_changed_record_keeps_other_table_and_input_immutable(self):
  original=fixture();data=bytearray(original);data[81]^=1;before=bytes(data)
  self.assertEqual([(x['table'],x['kind']) for x in issues(data)],[('One1','data')])
  fixed=update_tables(data,{'One1'});self.assertEqual(bytes(data),before);self.assertEqual(fixed[100:],original[100:]);self.assertEqual(issues(fixed),[])
  changed={i for i,(a,b) in enumerate(zip(fixed,before)) if a!=b};self.assertTrue(changed<=set(range(96,100)))
 def test_unrelated_bad_header_is_rejected_not_silently_rewritten(self):
  data=bytearray(fixture());data[132]^=1
  with self.assertRaises(ValueError):update_tables(data,{'One1'})
 def test_invalid_directory_cannot_write_outside_file(self):
  for offset,value in ((8,5),(16,999),(28,0xffffffff)):
   data=bytearray(fixture());struct.pack_into('<I',data,offset,value)
   with self.assertRaises(ValueError):issues(data)
  with self.assertRaises(ValueError):update_tables(fixture(),{'XXXX'})

if __name__=='__main__':unittest.main()
