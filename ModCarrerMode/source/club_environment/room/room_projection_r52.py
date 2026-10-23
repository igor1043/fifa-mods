import portable_paths as portable
"""Read-only projection of the active save for the match preview prototype."""
from pathlib import Path
import json,struct,sys,subprocess,xml.etree.ElementTree as ET
from server16_py.career_save_worker import blocks
from server16_py.career_read import Record

GAME=portable.GAME
TABLES={'teams','players','playernames','dcplayernames','editedplayernames','teamsheets','default_teamsheets','formations','teamplayerlinks','career_calendar'}

class Row(Record):
    def value(self,name):
        kind,bit,depth,low=self.fields[name]
        if kind==3:return self.GetIntField(name)
        if kind==0:
            raw=self.data[self.start+bit//8:self.start+(bit+depth)//8].split(b'\0',1)[0]
            try:return raw.decode('utf8')
            except UnicodeDecodeError:return raw.decode('cp1252')
        if kind==4 and depth==32 and bit%8==0:return struct.unpack_from('<f',self.data,self.start+bit//8)[0]
        raise ValueError('Unsupported field '+name)

def tables(data,metadata,spans,exclude=()):
    result={}
    for off,size in spans:
        count=struct.unpack_from('<I',data,off+16)[0];directory=off+24+count*8+4
        if data[off:off+4]!=b'DB\0\x08' or not 0<count<512:raise ValueError('Invalid DB')
        for n in range(count):
            short,rel=struct.unpack_from('<4sI',data,off+24+n*8)
            if short not in metadata:continue
            name,defs=metadata[short]
            if name not in TABLES or name in exclude:continue
            start=directory+rel;record_size=struct.unpack_from('<I',data,start+4)[0]
            allocated,valid=struct.unpack_from('<HH',data,start+16);nf=data[start+24];records=start+36+nf*16
            if not record_size or valid>allocated or records+allocated*record_size>off+size:raise ValueError('DB bounds')
            fields={}
            for k in range(nf):
                kind,bit,key,depth=struct.unpack_from('<II4sI',data,start+36+k*16)
                if key in defs:
                    d=defs[key];fields[d['name']]=(kind,bit,depth,int(d.get('rangelow',0)))
                    if bit+depth>record_size*8:raise ValueError(f'Field bounds: {name}.{d["name"]} kind={kind} bit={bit} depth={depth} bytes={record_size}')
            if name in result:raise ValueError('Ambiguous '+name)
            result[name]=[Row(data,records+i*record_size,fields) for i in range(valid)]
    return result

_base_cache=None
last_tables=None
def project(snapshot_path=GAME/'ModCarrerMode/runtime/career_fce_snapshot.json'):
    global _base_cache,last_tables
    snapshot=json.loads(snapshot_path.read_text(encoding='utf8'))
    if snapshot.get('schema')!=3:raise ValueError('Unsupported snapshot')
    path=Path(snapshot['savePath']);data=path.read_bytes()
    if len(data)!=snapshot['saveSize']:raise ValueError('Snapshot/save diverged')
    from server16_py.memory_access import Memory
    from server16_py.career_context import competition_session
    from server16_py.career_active_save import read_active_save
    import psutil
    process=psutil.Process(snapshot['pid'])
    if process.name().lower()!='fifa16.exe':raise ValueError('Not FIFA')
    m=Memory();m.process_id=process.pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,process.pid);m.base_module=m._get_base_address(process.exe())
    try:
        active=read_active_save(GAME,m);profile=competition_session(m,True)
        if active['path'].casefold()!=str(path).casefold() or active['process_created_100ns']!=snapshot['processCreated100ns'] or profile['club_id']!=snapshot['club']:raise ValueError('Stale career snapshot')
        if active['mtime_ns']//100+116444736000000000!=snapshot['saveWriteTime100ns']:raise ValueError('Snapshot belongs to another save revision')
        code=m.read_process_memory(m.base_module+0x44563f0,24)
        if code[7:9]!=b'\xc7\x01':raise ValueError('Calendar descriptor changed')
        index=struct.unpack_from('<I',code,9)[0]
        if not 0<=index<256:raise ValueError('Calendar registry bounds')
        calendar=m.read_int64(m.read_int64(profile['registry_address']+index*32+24))
        day,month,year=struct.unpack('<3i',m.read_process_memory(calendar+0x34,12));live_date=year*10000+month*100+day
        from datetime import datetime
        datetime.strptime(str(live_date),'%Y%m%d')
    finally:m.close()
    meta=ET.parse(GAME/'data/db/fifa_ng_db-meta.xml').getroot()
    metadata={t.get('shortname').encode():(t.get('name'),{f.get('shortname').encode():f.attrib for f in t.findall('fields/field')}) for t in meta.findall('table')}
    saved=tables(data,metadata,blocks(data));db_path=GAME/'data/db/fifa_ng_db.db';db_stat=db_path.stat();base_stamp=(db_stat.st_size,db_stat.st_mtime_ns)
    if _base_cache is None or _base_cache[0]!=base_stamp:
        base_data=db_path.read_bytes();_base_cache=(base_stamp,tables(base_data,metadata,[(0,len(base_data))],exclude=('playernames',)))
    base=_base_cache[1];last_tables=(str(path),snapshot['saveWriteTime100ns'],saved,base)
    rows=lambda name:saved[name] if name in saved else base.get(name,[])
    club=snapshot['club'];today=live_date
    fixtures=[r for r in snapshot['fixtures'] if len(r)>=10 and club in r[5:7] and r[3]>=today and r[9]==0]
    if not fixtures:
        empty=lambda ident:{'team_id':ident,'name':'','probable':ident!=club,'formation':'','players':[]}
        return {'available':False,'pid':process.pid,'save':str(path),'date':today,'fixture':[0,0,0,today,0,club,0,0,0,0,0],'user':empty(club),'opponent':empty(0)}
    fixture=min(fixtures,key=lambda r:(r[3],r[4],r[0]));opponent=fixture[6] if fixture[5]==club else fixture[5]
    players={r.value('playerid'):r for r in rows('players')}
    selected={r.value('playerid'+str(i)) for r in rows('teamsheets')+rows('default_teamsheets') if r.value('teamid') in (club,opponent) for i in range(11)}
    wanted={players[pid].value(key) for pid in selected if pid in players for key in ('commonnameid','playerjerseynameid','lastnameid')}
    here=portable.PREVIEW;request=here/'name_ids.json';cache_path=here/'base_name_cache.json';dbstat=(GAME/'data/db/fifa_ng_db.db').stat();stamp=[dbstat.st_size,dbstat.st_mtime_ns]
    cache=json.loads(cache_path.read_text(encoding='utf8')) if cache_path.exists() else {}
    if cache.get('stamp')!=stamp:cache={'stamp':stamp,'queried':[],'names':{}}
    missing=wanted-set(cache['queried'])
    if missing:
        request.write_text(json.dumps(sorted(missing)),encoding='utf8')
        from server16_py.fifa_db import _find_python32,_find_dll
        output=subprocess.run([str(_find_python32()),'-B',str(here/'names_worker.py'),str(_find_dll()),str(GAME/'data/db/fifa_ng_db.db'),str(GAME/'data/db/fifa_ng_db-meta.xml'),str(request)],check=True,capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        cache['names'].update(json.loads(output.stdout));cache['queried']=sorted(set(cache['queried'])|missing);cache_path.write_text(json.dumps(cache,ensure_ascii=False),encoding='utf8')
    names={int(k):v for k,v in cache['names'].items()}
    names.update({r.value('nameid'):r.value('name') for r in saved.get('dcplayernames',[])})
    teams={r.value('teamid'):r.value('teamname') for r in rows('teams')}
    edited={r.value('playerid'):r for r in rows('editedplayernames')}
    links={}
    for r in rows('teamplayerlinks'):links.setdefault(r.value('teamid'),set()).add(r.value('playerid'))
    def team(teamid,probable):
        options=[r for r in rows('teamsheets') if r.value('teamid')==teamid and r.value('isfavourite')==1]
        if len(options)>1:options=[]
        source='teamsheets' if options else 'default_teamsheets'
        if not options:options=[r for r in rows(source) if r.value('teamid')==teamid]
        if len(options)!=1:return {'team_id':teamid,'name':teams.get(teamid,''),'probable':probable,'source':'unavailable','formation':'','players':[],'portrait_ids':[]}
        sheet=options[0];line=[]
        for i in range(11):
            pid=sheet.value('playerid'+str(i))
            if pid<=0 or pid not in players or pid not in links.get(teamid,set()) or any(p['id']==pid for p in line):continue
            player=players[pid]
            if pid in edited:
                e=edited[pid];name=e.value('commonname') or e.value('playerjerseyname') or e.value('surname')
            else:name=next((names.get(player.value(key),'') for key in ('commonnameid','playerjerseynameid','lastnameid') if names.get(player.value(key),'')),'')
            if not name:name='' 
            line.append({'id':pid,'name':name,'overall':player.value('overallrating'),'position':sheet.value('position'+str(i)),'x':sheet.value('offset'+str(i)+'x'),'y':sheet.value('offset'+str(i)+'y')})
        bands=[]
        for p in sorted((p for p in line if p['position']!=0),key=lambda p:p['y']):
            if not bands or p['y']-bands[-1][0]>.09:bands.append([p['y'],1])
            else:bands[-1][1]+=1
        formation='-'.join(str(n) for _,n in bands)
        return {'team_id':teamid,'name':teams.get(teamid,''),'probable':probable,'source':source,'formation':formation,'players':line,
                'portrait_ids':sorted(pid for pid in links.get(teamid,set()) if pid in players)}
    return {'pid':process.pid,'save':str(path),'date':today,'fixture':fixture,'user':team(club,False),'opponent':team(opponent,True)}

if __name__=='__main__':
    p=Path(__file__).with_name('lineups.json');data=project();p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(data,ensure_ascii=False,indent=2))
