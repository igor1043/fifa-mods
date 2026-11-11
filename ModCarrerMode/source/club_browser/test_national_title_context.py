import struct,unittest
from national_title_context import TEAM_GETTER,live_team,observations

class Memory:
    base_module=1000
    def __init__(self,club=1043,nation=1370):self.club=club;self.nation=nation
    def read_process_memory(self,address,size):
        if address==1000+0x5ac5940:return TEAM_GETTER
        return struct.pack('<i',self.club if address==2000+0x1a4 else self.nation)

class NationalContextTests(unittest.TestCase):
    def test_second_slot_is_a_concurrent_national_job_not_a_club_change(self):
        profile=dict(context_address=2000,club_id=1043)
        self.assertEqual(1370,live_team(Memory(),profile))
        self.assertEqual(0,live_team(Memory(nation=-1),profile))
        with self.assertRaises(ValueError):live_team(Memory(club=1),profile)
    def test_only_valid_nations_and_actual_observation_dates_are_used(self):
        profile=dict(context_address=2000,club_id=1043)
        rows=observations(dict(nationalteamid=-1),{},20261203,20270103,{1370},Memory(),profile)
        self.assertEqual([(20261203,0),(20270103,1370)],[(r['date'],r['team']) for r in rows])
        rows=observations(dict(nationalteamid=1370),dict(internationalteamid=999),20261203,20270103,{1370})
        self.assertEqual([],rows)

if __name__=='__main__':unittest.main()
