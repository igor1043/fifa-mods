import struct,unittest
from unittest.mock import patch
from room_coach_scouting import read_network,enrich,from_tables


class Row:
    def __init__(self,**values):self.fields=values
    def value(self,key):return self.fields[key]


def record(ident,name,country,nation):
    first,last=name.split(' ',1)
    return struct.pack('<i',ident)+first.encode().ljust(45,b'\0')+last.encode().ljust(45,b'\0')+struct.pack('<9i',country,nation,2,4,2,10000,111111,0,-1)


def payload():
    return (b'X'*160+b'gtn02\0'+struct.pack('<2i',20261209,1)+record(0,'Primeiro Olheiro',45,54)+
            struct.pack('<i',1)+record(0,'Outro Olheiro',0,54)+b'\0'*124+
            b'gtn05\0'+struct.pack('<6i',12345,67890,2,12,2026,2)+struct.pack('<10i',100,1114112,168,20261201,-1,200,1048576,168,20261102,-1)+b'END')


class ScoutingTests(unittest.TestCase):
    def test_reads_career_network_and_hired_scouts_only_without_mutation(self):
        raw=bytearray(payload());before=bytes(raw);result=read_network(raw,{100,200})
        self.assertTrue(result['recognized']);self.assertEqual(len(result['scouts']),1)
        self.assertEqual(result['scouts'][0]['country'],45)
        self.assertEqual([p['id'] for p in result['reports']],[100,200])
        self.assertEqual(bytes(raw),before)

    def test_shortlist_is_not_inferred_from_global_transfer_list(self):
        self.assertFalse(read_network(b'X'*500,{100})['recognized'])
        rows=lambda n:[Row(playerid=100,teamid=1)] if n=='career_transferlist' else []
        self.assertEqual(from_tables(rows,{'career_transferlist'},{100})['reports'],[])

    def test_duplicate_or_truncated_serializers_are_unavailable(self):
        for raw in (payload()+b'gtn05\0',payload()+b'gtn02\0',payload()[:-20]):
            self.assertFalse(read_network(raw,{100,200})['recognized'])

    def test_negative_or_oversized_vectors_cannot_cross_bounds(self):
        for count in (-1,999999):
            raw=bytearray(payload());struct.pack_into('<i',raw,170,count)
            self.assertFalse(read_network(raw)['recognized'])

    def test_deleted_players_and_invalid_dates_are_not_fabricated(self):
        self.assertEqual([p['id'] for p in read_network(payload(),{100})['reports']],[100])
        raw=bytearray(payload());start=raw.index(b'gtn05\0')+6
        struct.pack_into('<i',raw,start+24+12,20261335)
        self.assertFalse(read_network(raw)['recognized'])

    def test_default_database_cannot_supply_another_careers_scouts(self):
        calendar=Row();calendar.data=payload()
        self.assertFalse(from_tables(lambda _: [calendar],set(),{100,200})['recognized'])

    def test_player_links_choose_the_club_not_the_national_team(self):
        tables={'nations':[Row(nationid=54,nationname='Brazil',isocountrycode='BR')],
                'players':[Row(playerid=100,playerjerseynameid=1,preferredposition1=24,nationality=54)],
                'teams':[Row(teamid=10,teamname='Clube'),Row(teamid=20,teamname='Seleção')],
                'teamplayerlinks':[Row(playerid=100,teamid=20),Row(playerid=100,teamid=10)],
                'teamnationlinks':[Row(teamid=20)]}
        result=enrich({},lambda n:tables.get(n,[]),set(),read_network(payload(),{100}),{1:'Atacante'})
        self.assertEqual(result['reports'][0]['club'],10)
        self.assertEqual(result['reports'][0]['name'],'Atacante')
        self.assertEqual(result['reports'][0]['nationality']['name'],'Brasil')
        self.assertEqual(result['youth'],[])

    def test_youth_missions_remain_distinct_and_career_local(self):
        tables={'career_scouts':[Row(scoutid=3)],'career_scoutmission':[Row(scoutid=3,nationality=54,returningdate=20270101)]}
        base=enrich({},lambda n:tables.get(n,[]),set(),read_network(payload(),{1}),{})
        own=enrich({},lambda n:tables.get(n,[]),set(tables),read_network(payload(),{1}),{})
        self.assertEqual(base['youth'],[]);self.assertEqual(len(own['youth']),1)


if __name__=='__main__':unittest.main()
