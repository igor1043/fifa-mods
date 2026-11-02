import struct,unittest
from saved_competitions import read

class SavedCompetitionTest(unittest.TestCase):
 def test_saved_league_five_games_does_not_use_seed_as_wins(self):
  def node(slot,kind,key,name,parent):
   return struct.pack('<HBHB',slot,1,slot,kind)+key.encode().ljust(6,b'\0')+name.encode().ljust(33,b'\0')+struct.pack('<h',parent)
  nodes=b''.join((node(0,0,'','FIFA',-1),node(1,3,'C53','TrophyName_Abbr15_53',0),node(2,4,'','FCE_Setup_Stage',1),node(3,5,'','Group',2)))
  standing=bytearray(21);struct.pack_into('<HBHi',standing,0,0,1,3,241);standing[9]=19;standing[10]=3;standing[15]=2;standing[20]=15
  raw=b'padding!'+nodes+b''.join(bytes(n) for n in (10,21,12,20,10,14))+standing
  s=read(raw,20260810);self.assertEqual([0,3,241,3,0,0,2,0,0,5],s['standings'][0]);self.assertEqual('career_file',s['source']);self.assertEqual([],s['fixtures'])
 def test_unknown_structure_does_not_fall_back_to_ram(self):
  with self.assertRaises(ValueError):read(b'not a save',20260810)

if __name__=='__main__':unittest.main()
