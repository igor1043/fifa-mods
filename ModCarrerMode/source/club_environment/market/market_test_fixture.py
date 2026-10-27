"""Synthetic career tables for portable read-only market tests, no personal save."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import struct, tempfile, zlib
import read_market

class TableSet:
    def __init__(self, data):
        self.data=data
        self.tables={name:{'fields':set().union(*(row.keys() for row in rows)) if rows else set()} for name,rows in data.items()}
    def rows(self, name, fields):
        return [{field:row.get(field,0) for field in fields} for row in self.data.get(name,[])]

@contextmanager
def career_fixture(count=20):
    with tempfile.TemporaryDirectory(prefix='Mercado carreira sintética á ') as temporary:
        game=Path(temporary);db=game/'data/db';db.mkdir(parents=True)
        (db/'fifa_ng_db.db').write_bytes(b'catalog fixture')
        fields=''.join(f'<field name="{name}" shortname="{short}" rangelow="1"/>' for name,short in
            (('currdate','date'),('start1','sUgA'),('end1','PpdA'),('start2','Jdde'),('end2','igYC')))
        (db/'fifa_ng_db-meta.xml').write_text('<database><table name="career_calendar">'+fields+'</table></database>')
        teams=[dict(teamid=1,teamname='Clube origem'),dict(teamid=1043,teamname='Clube destino'),dict(teamid=1629,teamname='Outro clube')]
        players=[dict(playerid=234+i,commonnameid=10+i,firstnameid=10+i,lastnameid=10+i,overallrating=82,potential=86,preferredposition1=25) for i in range(count)]
        roster=TableSet(dict(teams=teams,players=players,teamplayerlinks=[dict(playerid=p['playerid'],teamid=1043) for p in players],
            leagueteamlinks=[dict(teamid=t['teamid'],leagueid=1,secondarytable=0) for t in teams]))
        calendar=TableSet(dict(career_users=[dict(userid=1,clubteamid=1629,firstname='Manager',surname='Fixture')],
            career_calendar=[dict(currdate=20260101,start1=101,end1=131,start2=701,end2=831)]))
        offers=TableSet(dict(career_transferoffer=[dict(offerid=i+1,result=32,offeredfee=2_000_000,teamid=1,offerteamid=1043,
            snipedteamid=0,playerid=p['playerid'],exchangeplayerid=0,date=20260101,stage=1,iscputransfer=1,isloan=0,isloanbuy=0,issnipe=0) for i,p in enumerate(players)],career_precontract=[]))
        base=TableSet(dict(teams=teams,leagues=[dict(leagueid=1,leaguename='Liga de teste',level=1)],
            leagueteamlinks=roster.data['leagueteamlinks'],playernames=[dict(nameid=10+i,name='Jogador '+str(i+1)) for i in range(count)]))
        raw=bytearray(160)
        for ident in range(3):raw+=b'DB\0\x08'+struct.pack('<5I',0,24,0,1,ident)
        struct.pack_into('<I',raw,136,56);struct.pack_into('<I',raw,132,zlib.crc32(raw[160:]))
        slot=game/'slot';slot.mkdir();save=slot/'DATA';save.write_bytes(raw)
        def database(_,data,**kwargs):return (roster,calendar,offers)[struct.unpack_from('<I',data,20)[0]]
        with patch.object(read_market,'FifaDatabase',side_effect=database),patch.object(read_market,'_catalog',return_value=base):
            yield game,save
