"""Read-only local career preview; renders are generated per selected club."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
from threading import RLock, Thread
from urllib.parse import urlparse, parse_qs
import struct, datetime, shutil, time, base64, argparse, configparser, hashlib, json, os, sys, traceback, subprocess, tempfile
from fifa_db import FifaDatabase
from club_save_details import build_detail, _pack_fixture, ATTRIBUTE_FIELDS, APPEARANCE_FIELDS
from PIL import Image
from web_model import convert
ROOT=Path(__file__).resolve().parent
PREVIEW_SAVES=Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))/'FIFA Friends/preview-saves'
GAME_SOURCE_LOCK=RLock()
SELECTION=PREVIEW_SAVES/'selected.json'
NATIVE=ROOT.parent.parent/'source/career_native'
sys.path.insert(0,str(ROOT.parent/'career_birthdate_2006'))
import birthdate_editor

class Career:
    def __init__(self,game=None,save=None):
        cfg=configparser.ConfigParser();cfg.read(ROOT/'clubes.ini',encoding='utf-8-sig')
        self.game=Path(game or cfg['fifa']['game_path']);self.slot=cfg['fifa']['sample_save_slot']
        self.save=Path(os.environ['USERPROFILE'])/'Documents/FIFA 16/0/FIFA16'/self.slot/'DATA'
        if save is None and SELECTION.is_file():
            try:save=json.loads(SELECTION.read_text(encoding='utf-8'))['path']
            except (ValueError,KeyError,OSError):pass
        if save and Path(save).is_file():self.save=Path(save);self.slot=Path(save).parent.name
        self.lock=RLock();self.model_lock=RLock();self.last_model_request=time.monotonic();self.warmed=set();self.retired=False;self.pool=ThreadPoolExecutor(max_workers=1)
        self.details={};self.pending=set();self.revision=None;self.worker=None;self.calendar={};self.render_errors={};self.reader=ThreadPoolExecutor(max_workers=1)
    def refresh(self):
        revision=(self.save.stat().st_mtime_ns,self.save.stat().st_size)
        if revision==self.revision:return
        raw=self.save.read_bytes();self.calendar=self.read_calendar(raw);self.base=FifaDatabase(self.game,include_all_tables=True);self.schedule=self.read_schedule(raw)
        self.db=None;self.managers={};self.history=[];manager_stats={}
        for outer in birthdate_editor.find_databases(raw):
            db=FifaDatabase(self.game,raw[outer.start:outer.start+outer.declared_size],include_all_tables=True)
            if {'teams','teamplayerlinks','players'}<=db.tables.keys():self.db=db
            if 'manager' in db.tables:
                for row in db.rows('manager',['firstname','surname','teamid']):
                    if row.get('teamid'):self.managers[row['teamid']]=row
            if 'career_managerinfo' in db.tables:
                for row in db.rows('career_managerinfo',['clubteamid','boardconfidence','managerreputation','wage']):
                    if row.get('clubteamid',-1)>0:manager_stats[row['clubteamid']]=row
            if 'career_managerhistory' in db.tables:
                self.history+=db.rows('career_managerhistory',['season','leagueid','teamid','games_played','wins','draws','losses','goals_for','goals_against','points','tableposition','leaguetrophies','domesticcuptrophies','continentaltrophies'])
        for club,row in manager_stats.items():self.managers.setdefault(club,{}).update(row)
        if self.db is None:raise ValueError('O save não contém o banco do elenco.')
        old_tag=getattr(self,'tag','')
        self.pose_players={};self.pose_teams={};self.pose_links={};self.details={};self.render_errors={};self.context_cache=None;self.revision=revision;self.tag=hashlib.sha256(raw).hexdigest()[:16]
        if old_tag and old_tag!=self.tag:
            def clear_previous_revision():
                with self.model_lock:purge_generated(old_tag)
            Thread(target=clear_previous_revision,daemon=True).start()
    @staticmethod
    def read_calendar(raw):
        fields={"careerDate":b"aLZZ","windowStart1":b"sUgA","windowEnd1":b"PpdA","windowStart2":b"Jdde","windowEnd2":b"igYC"}
        for database in birthdate_editor.find_databases(raw):
            table=birthdate_editor.find_table(database,b"GJUr")
            if table is None or not table.written:continue
            descriptors={name:birthdate_editor.find_field(table,short) for name,short in fields.items()}
            if descriptors["careerDate"] is None:continue
            offset=birthdate_editor.row_offset(database,table,0)
            value=lambda name:birthdate_editor.read_packed(raw,offset,descriptors[name]) if descriptors[name] else 0
            dates={name:(value(name)+101 if descriptors[name] else 0) for name in fields if name!="careerDate"}
            return {"careerDate":value("careerDate"),"windowEndsValid":all(dates.get(key,0)>0 for key in ("windowStart1","windowEnd1","windowStart2","windowEnd2")),**dates}
        return {}
    @staticmethod
    def read_schedule(raw):
        # Saved FCE tables omit in-memory pointers/padding; row IDs validate boundaries.
        marker=raw.find(b'FCE_Setup_Stage')
        start=marker-12-2*47
        if marker<0 or start<0:return []
        def block(offset,stride):
            rows=[]
            for index in range(65536):
                if offset+stride>len(raw) or struct.unpack_from('<H',raw,offset)[0]!=index:break
                rows.append(raw[offset:offset+stride]);offset+=stride
            return rows,offset
        nodes,offset=block(start,47)
        if len(nodes)<3 or nodes[0][12:16]!=b'FIFA':return []
        assignments,offset=block(offset,10)
        fixtures,offset=block(offset,21)
        rounds,offset=block(offset,12)
        entrants,offset=block(offset,20)
        pools,offset=block(offset,10)
        periods,offset=block(offset,14)
        standings,offset=block(offset,21)
        if not all((nodes,assignments,fixtures,rounds,entrants,pools,periods,standings)):return []
        objects={struct.unpack_from('<H',r,3)[0]:r for r in nodes if r[2]==1}
        teams={struct.unpack_from('<H',r,0)[0]:struct.unpack_from('<i',r,5)[0] for r in standings if r[2]==1}
        result=[]
        for row in fixtures:
            if row[2]!=1:continue
            date=struct.unpack_from('<I',row,6)[0]
            try:datetime.date(date//10000,date//100%100,date%100)
            except ValueError:continue
            home=teams.get(struct.unpack_from('<H',row,12)[0],-1);away=teams.get(struct.unpack_from('<H',row,16)[0],-1)
            if home<0 or away<0 or home==away:continue
            root=struct.unpack_from('<H',row,3)[0];visited=set();asset=0
            while root in objects and root not in visited:
                visited.add(root);node=objects[root]
                if node[5]==3:
                    key=node[6:12].split(b'\0',1)[0].decode('ascii',errors='ignore')
                    title=node[12:45].split(b'\0',1)[0].decode('ascii',errors='ignore')
                    identity=title.removeprefix('TrophyName_Abbr15_') if title.startswith('TrophyName_Abbr15_') else key[1:] if key.startswith('C') else ''
                    asset=int(identity) if identity.isdigit() else 0;break
                root=struct.unpack_from('<h',node,45)[0]
            time_value=struct.unpack_from('<H',row,10)[0]
            result.append({'id':struct.unpack_from('<H',row,0)[0],'home':home,'away':away,'root':root,'asset':asset,'date':date,'time':f'{time_value//100:02d}:{time_value%100:02d}','stage':struct.unpack_from('<H',row,3)[0],'homeScore':row[14] if row[14]!=255 else None,'awayScore':row[18] if row[18]!=255 else None,'played':bool(row[20]),'score':f'{row[14]} – {row[18]}' if row[20] else '—'})
        return result
    def context(self):
        with self.lock:
            self.refresh()
            candidates=[club for club,manager in self.managers.items() if manager.get('clubteamid')==club]
            if len(candidates)!=1:
                candidates=[club for club,manager in self.managers.items() if manager.get('teamid')==club]
            if len(candidates)!=1:raise ValueError('Não foi possível identificar um único clube da carreira neste save.')
            club=candidates[0]
            result=self.get(club,render=True)
            context_key=(self.tag,club,id(result['detail']),result['renderPending'],result.get('renderError'))
            if self.context_cache and self.context_cache[0]==context_key:return self.context_cache[1]
            detail=dict(result['detail'])
            team_names={r['teamid']:r['teamname'] for r in self.db.rows('teams',['teamid','teamname'])}
            league_names={r['leagueid']:r['leaguename'] for r in self.base.rows('leagues',['leagueid','leaguename'])}
            matches=[{**m,'homeName':team_names.get(m['home'],'Clube'),'awayName':team_names.get(m['away'],'Clube'),'competition':league_names.get(m['asset'],'Competição')} for m in self.schedule if club in (m['home'],m['away'])]
            matches.sort(key=lambda m:(m['date'],m['time'],m['id']))
            current=self.calendar.get('careerDate',0)
            upcoming=[m for m in matches if not m['played'] and m['date']>=current]
            previous=[m for m in matches if m['played'] and m['date']<=current]
            competitions=[]
            for root in dict.fromkeys(m['root'] for m in matches):
                club_matches=[m for m in matches if m['root']==root]
                stage=(next((m for m in club_matches if not m['played'] and m['date']>=current),None) or club_matches[-1])['stage']
                fixtures=[m for m in self.schedule if m['root']==root and m['stage']==stage]
                asset=club_matches[0]['asset'];table={}
                for m in fixtures:
                    for team in (m['home'],m['away']):table.setdefault(team,{'team':team,'name':team_names.get(team,'Clube'),'games':0,'wins':0,'draws':0,'losses':0,'goalsFor':0,'goalsAgainst':0,'points':0,'form':[]})
                for m in sorted(fixtures,key=lambda m:(m['date'],m['id'])):
                    if not m['played'] or m['date']>current or m['homeScore'] is None or m['awayScore'] is None:continue
                    for team,gf,ga in [(m['home'],m['homeScore'],m['awayScore']),(m['away'],m['awayScore'],m['homeScore'])]:
                        row=table[team];row['games']+=1;row['goalsFor']+=gf;row['goalsAgainst']+=ga;outcome='V' if gf>ga else 'D' if gf<ga else 'E';row[{'V':'wins','D':'losses','E':'draws'}[outcome]]+=1;row['points']+=3 if outcome=='V' else 1 if outcome=='E' else 0;row['form']=(row['form']+[outcome])[-5:]
                ordered=sorted(table.values(),key=lambda r:(-r['points'],-r['wins'],-(r['goalsFor']-r['goalsAgainst']),-r['goalsFor'],r['name']))
                for rank,row in enumerate(ordered,1):row['rank']=rank
                competitions.append({'root':root,'asset':asset,'name':league_names.get(asset,'Competição'),'table':ordered if len(ordered)>=3 else [],'goals':[],'assists':[]})
            detail['webDashboard']={**detail.get('webDashboard',{}),'competitions':competitions,'current':upcoming[0]['root'] if upcoming else competitions[0]['root'] if competitions else None,'calendar':matches,'upcoming':upcoming,'previous':previous,'careerDate':current}
            detail['nextMatch']=upcoming[0] if upcoming else None
            warm_key=(self.tag,club)
            if warm_key not in self.warmed and len(detail.get('starters',[]))==11:
                self.warmed.add(warm_key);self.pool.submit(self.prewarm,club,self.tag)
            payload={'clubId':club,'clubName':detail['name'],'detail':detail,'calendar':dict(self.calendar),'saveSlot':self.slot,'saveFile':self.save.name,'saveRevision':self.tag,'source':'local-save','savedAt':self.save.stat().st_mtime,'playerCount':len(detail.get('players',[])),'renderPending':result['renderPending'],'renderError':result.get('renderError')}
            self.context_cache=(context_key,payload)
            return payload
    def make(self,club,render):
        return build_detail(ROOT,NATIVE,self.game,self.db,self.base,club,saved_manager=self.managers.get(club),history_records=self.history,render_native=render,asset_revision=self.tag+'-r2')
    def get(self,club,render=True):
        with self.lock:
            self.refresh()
            if club not in self.details:
                cached=ROOT/'assets/club-details'/f'profile-v9-{self.tag}-{club}.json'
                value=json.loads(cached.read_text(encoding='utf-8')) if cached.is_file() else None
                if value and value.get('lineupScene') and not (ROOT/value['lineupScene']).is_file():value=None
                self.details[club]=value or self.make(club,False)
            detail=self.details[club]
            if render and detail and detail.get('starters') and not detail.get('lineupScene') and club not in self.pending and club not in self.render_errors:
                self.pending.add(club);self.pool.submit(self.render,club,self.tag)
            return {'detail':detail,'renderPending':club in self.pending,'renderError':self.render_errors.get(club),'saveSlot':self.slot}
    def render(self,club,tag):
        try:
            detail=self.make(club,True)
            with self.lock:
                if not self.retired and tag==self.tag:
                    if not detail.get('lineupScene'):self.render_errors[club]='Não foi possível renderizar os titulares deste save.'
                    self.details[club]=detail
                    path=ROOT/'assets/club-details'/f'profile-v9-{tag}-{club}.json';path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps(detail,ensure_ascii=False),encoding='utf-8')
        except Exception as error:
            traceback.print_exc()
            with self.lock:self.render_errors[club]=str(error)
        finally:
            with self.lock:self.pending.discard(club)
    def prewarm(self,club,tag):
        for player,pose in [(-1,1),(0,201),(-3,301),(-3,302),(-3,303),(-3,304)]:
            if self.retired or self.tag!=tag:return
            while time.monotonic()-self.last_model_request<8:
                if self.retired or self.tag!=tag:return
                time.sleep(.5)
            try:self.pose(club,player,pose,model=True,background=True)
            except Exception as error:print('Pré-cache 3D:',club,pose,str(error))
    def pose(self,club,player,pose,model=False,background=False):
        if not background:self.last_model_request=time.monotonic()
        if model and self.revision==(self.save.stat().st_mtime_ns,self.save.stat().st_size):
            folder=ROOT/'assets/runtime-cache/interactive-models'/f'{self.tag}-{club}-{player}-{pose}-r3'
            target=folder/'model.json'
            if target.is_file() and (folder/'geometry.bin').is_file():
                os.utime(folder,None)
                return {'image':'http://127.0.0.1:8876/'+target.relative_to(ROOT).as_posix()}
        if not ((301<=pose<=304 if player==-3 else pose==120 if player==-2 else 1<=pose<=7) if player<0 else (pose in (201,202,203,204,208,209,210) if player==0 else 101<=pose<=114)):raise ValueError('Pose inválida')
        with self.model_lock:
            with self.lock:
                self.refresh()
                if not self.pose_links:
                    for row in self.db.rows('teamplayerlinks',['teamid','playerid','position','jerseynumber']):self.pose_links.setdefault((row['teamid'],row['playerid']),[]).append(row)
                links=self.pose_links.get((club,player),[]) if player else next((rows for (team,pid),rows in self.pose_links.items() if team==club and rows),[])
                if player<0:links=[row for (team,pid),items in self.pose_links.items() if team==club for row in items if player==-2 or (player==-3 and pose==302) or 0<=row['position']<=27];links.sort(key=lambda row:row['position'])
                if not links or (player>=0 and len(links)!=1):raise ValueError('Jogador não pertence ao clube neste save')
                fields=['playerid','commonnameid','firstnameid','lastnameid','preferredposition1','overallrating',*ATTRIBUTE_FIELDS,*APPEARANCE_FIELDS]
                if not self.pose_players:self.pose_players={r['playerid']:r for r in self.db.rows('players',fields)}
                actor=player or links[0]['playerid'];rows={r['playerid']:self.pose_players[r['playerid']] for r in links if r['playerid'] in self.pose_players} if player<0 else ({actor:self.pose_players[actor]} if actor in self.pose_players else {})
                if not self.pose_teams:self.pose_teams={r['teamid']:r for r in self.db.rows('teams',['teamid','teamname','teamcolor1r','teamcolor1g','teamcolor1b'])}
                teams=[self.pose_teams[club]] if club in self.pose_teams else []
                if not teams or not rows:raise ValueError('Jogador ausente no save')
                export_tag=self.tag
                target=ROOT/'assets/runtime-cache/player-poses'/f'{self.tag}-{club}-{player}-{pose}.webp'
                folder=ROOT/'assets/runtime-cache/interactive-models'/f'{self.tag}-{club}-{player}-{pose}-r3'
                if model:target=folder/'model.json'
            if not target.is_file():
                executable=NATIVE/'build/previews/generate_club_details_preview/generate_club_details_preview.exe'
                if not executable.is_file():executable=ROOT/'native/generate_club_details_preview.exe'
                with tempfile.TemporaryDirectory(prefix='fifa-player-pose-') as temp:
                    temp=Path(temp);fixture=temp/'player.bin';image=temp/'player.png'
                    names={r['nameid']:r['name'] for r in self.base.rows('playernames',['nameid','name'])}
                    if 'dcplayernames' in self.db.tables:names.update({r['nameid']:r['name'] for r in self.db.rows('dcplayernames',['nameid','name'])})
                    edited={r['playerid']:r for r in self.db.rows('editedplayernames',['playerid','firstname','surname','commonname','playerjerseyname'])} if 'editedplayernames' in self.db.tables else {}
                    fixture.write_bytes(_pack_fixture(club,teams[0]['teamname'],teams[0],rows,[(r['position'],r) for r in links],names,edited))
                    if model:
                        if self.worker is None or self.worker.poll() is not None:self.worker=subprocess.Popen([str(executable),'--web-worker',str(self.game)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
                        self.worker.stdin.write(str(fixture)+'\t'+str(image)+'\t'+str(pose)+'\n');self.worker.stdin.flush()
                        def completed():
                            while True:
                                line=self.worker.stdout.readline()
                                if not line:raise ValueError('O renderizador 3D foi encerrado')
                                if line.startswith('FF_READY'):return line.strip()
                        try:
                            status=self.reader.submit(completed).result(timeout=180 if player<0 else 45)
                            if status!='FF_READY 0':raise ValueError('Modelo 3D indisponível para este jogador')
                        except Exception:
                            self.worker.kill();self.worker=None;raise
                    else:subprocess.run([str(executable),'--player',str(self.game),str(fixture),str(image),str(pose),'0'],check=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
                    target.parent.mkdir(parents=True,exist_ok=True)
                    if model:convert(image,folder)
                    else:
                        with Image.open(image) as bitmap:
                            box=bitmap.convert('RGBA').getchannel('A').getbbox();bitmap.crop(box or (0,0,bitmap.width,bitmap.height)).save(target,'WEBP',quality=90)
            if self.retired or export_tag!=self.tag:raise ValueError('A carreira mudou. Abra a cena novamente.')
            os.utime(folder,None) if folder.is_dir() else None
            return {'image':'http://127.0.0.1:8876/'+target.relative_to(ROOT).as_posix()}

GENERATED_CACHE_TTL=7*24*60*60

def _remove_cache_entry(entry,parent):
    try:
        if entry.resolve().parent!=parent.resolve():return
        if entry.is_dir():shutil.rmtree(entry,ignore_errors=True)
        else:entry.unlink(missing_ok=True)
    except OSError:
        pass

def purge_generated(tag):
    if len(tag)!=16 or any(c not in '0123456789abcdef' for c in tag):return
    cache_roots=[ROOT/'assets/runtime-cache'/category for category in ('renders','interactive-models','player-poses')]
    cache_roots.extend(ROOT/'assets'/category for category in ('interactive-models','player-poses'))
    for base in cache_roots:
        if not base.is_dir():continue
        for entry in list(base.glob(tag+'*'))+list(base.glob('textures-'+tag)):
            _remove_cache_entry(entry,base)
    details=ROOT/'assets/club-details'
    for pattern in (tag+'-*.json','profile-v*-'+tag+'-*.json'):
        for entry in details.glob(pattern):_remove_cache_entry(entry,details)

def purge_expired_generated():
    cutoff=time.time()-GENERATED_CACHE_TTL
    cache_roots=[(ROOT/'assets/runtime-cache',True)]
    cache_roots.extend((ROOT/'assets'/category,False) for category in ('interactive-models','player-poses'))
    for root,nested in cache_roots:
        if not root.is_dir():continue
        folders=[entry for entry in root.iterdir() if entry.is_dir()] if nested else [root]
        for folder in folders:
            for entry in list(folder.iterdir()):
                if entry.name=='textures':continue
                try:
                    if entry.stat().st_mtime<cutoff:_remove_cache_entry(entry,folder)
                except OSError:
                    pass
    details=ROOT/'assets/club-details'
    if details.is_dir():
        for entry in details.glob('*.json'):
            try:
                if entry.stat().st_mtime<cutoff:_remove_cache_entry(entry,details)
            except OSError:
                pass

def retire_preview(old,current):
    old.retired=True
    def cleanup():
        old.pool.shutdown(wait=True,cancel_futures=True)
        with old.model_lock:
            if old.worker and old.worker.poll() is None:old.worker.terminate()
            old.reader.shutdown(wait=False,cancel_futures=True)
            tag=getattr(old,'tag','')
            if tag and tag!=getattr(current,'tag',''):purge_generated(tag)
            old_folder=old.save.parent.resolve()
            if old_folder.parent==PREVIEW_SAVES.resolve() and old_folder!=current.save.parent.resolve():shutil.rmtree(old_folder)
    Thread(target=cleanup,daemon=True).start()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        origin=self.headers.get('Origin','')
        if origin in ('http://127.0.0.1:8876','http://localhost:8876','https://fifa-friends.local'):self.send_header('Access-Control-Allow-Origin',origin)
        self.send_header('Access-Control-Allow-Private-Network','true')
        self.send_header('Cache-Control','private, max-age=604800, immutable' if urlparse(self.path).path.startswith('/assets/runtime-cache/') else 'no-cache');super().end_headers()
    def do_OPTIONS(self):
        self.send_response(204);self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type');self.end_headers()
    def do_POST(self):
        if urlparse(self.path).path=='/api/cache/clear':
            if self.headers.get('Origin','') not in ('http://127.0.0.1:8876','http://localhost:8876'):return self.json({'error':'Somente na prévia local.'},403)
            career=self.server.career
            with career.model_lock,career.lock:
                if career.pending:return self.json({'error':'Aguarde a geração dos cards terminar antes de limpar.'},409)
                for folder in (ROOT/'assets/runtime-cache',ROOT/'assets/interactive-models',ROOT/'assets/player-poses',ROOT/'assets/club-details'):
                    if folder.is_dir():shutil.rmtree(folder)
                career.details.clear();career.render_errors.clear();career.warmed.clear()
            return self.json({'cleared':True})
        if urlparse(self.path).path!='/api/career/select':return self.json({'error':'Rota não encontrada'},404)
        if self.headers.get('Origin','') not in ('http://127.0.0.1:8876','http://localhost:8876'):return self.json({'error':'Seleção disponível somente na prévia local.'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=128*1024*1024:raise ValueError('Selecione um save de até 128 MB.')
            payload=self.rfile.read(size)
            if len(payload)!=size:raise ValueError('Arquivo incompleto.')
            index=None
            if self.headers.get('Content-Type','').startswith('application/json'):
                bundle=json.loads(payload)
                raw=base64.b64decode(bundle['DATA'],validate=True)
                index=base64.b64decode(bundle['INDEX'],validate=True)
                if not index:raise ValueError('O arquivo INDEX está vazio.')
            else:raw=payload
            title=raw[16:80].split(b'\0',1)[0].decode('utf-8',errors='replace')
            if title.casefold().startswith('configura'):
                raise ValueError('Esta pasta é de '+title+', não de uma carreira. Escolha a pasta do save do modo carreira.')
            PREVIEW_SAVES.mkdir(parents=True,exist_ok=True)
            folder=PREVIEW_SAVES/hashlib.sha256(raw).hexdigest()
            folder.mkdir(exist_ok=True)
            target=folder/'DATA'
            target.write_bytes(raw)
            if index is not None:(folder/'INDEX').write_bytes(index)
            candidate=Career(str(self.server.career.game),save=target)
            try:context=candidate.context()
            except Exception:
                candidate.pool.shutdown(wait=False);candidate.reader.shutdown(wait=False)
                raise ValueError('Esse arquivo não contém um save de carreira compatível. Selecione o arquivo DATA da carreira.')
            old=self.server.career;self.server.career=candidate
            SELECTION.write_text(json.dumps({'path':str(target)}),encoding='utf-8')
            retire_preview(old,candidate)
            return self.json(context)
        except Exception as error:return self.json({'error':str(error)},400)
    def career_source(self):
        query=parse_qs(urlparse(self.path).query)
        if query.get('source')!=['game']:return self.server.career
        with GAME_SOURCE_LOCK:
            bridge=self.server.career.game/'ModCarrerMode/runtime/career_active_save.tsv'
            fields=dict(line.split('=',1) for line in bridge.read_text(encoding='utf-8',errors='replace').splitlines() if '=' in line)
            pid=fields.get('pid')
            source=Path(fields.get('path',''))
            live=getattr(self.server,'live_career',None)
            valid=source.is_file() and source.name.upper()=='DATA'
            if not valid:
                if live is not None and getattr(self.server,'live_pid',None)==pid:return live
                active=int(query.get('activeClub',['0'])[0])
                recovered=bridge.parent/'career_web_source.json'
                if active<=0 and recovered.is_file():
                    try:
                        remembered=json.loads(recovered.read_text(encoding='utf-8'))
                        if remembered.get('pid')==pid:active=int(remembered.get('club',0))
                    except (OSError,ValueError):pass
                if active<=0:raise ValueError('Aguardando identificação da carreira ativa pelo jogo.')
                candidates=[]
                root=Path(os.environ['USERPROFILE'])/'Documents/FIFA 16/0/FIFA16'
                for path in sorted(root.glob('*/DATA'),key=lambda p:p.stat().st_mtime,reverse=True):
                    if path.stat().st_size<1000000:continue
                    raw=path.read_bytes()
                    try:
                        clubs=set()
                        for outer in birthdate_editor.find_databases(raw):
                            db=FifaDatabase(self.server.career.game,raw[outer.start:outer.start+outer.declared_size],include_all_tables=True)
                            if 'career_managerinfo' in db.tables:clubs.update(r.get('clubteamid') for r in db.rows('career_managerinfo',['clubteamid']))
                        if clubs=={active}:candidates.append(path)
                    except Exception:continue
                if not candidates:raise ValueError('Nenhum save corresponde ao clube ativo do jogo. Salve a carreira e reabra a tela.')
                source=candidates[0]
                recovered.write_text(json.dumps({'pid':pid,'club':active,'path':str(source)}),encoding='utf-8')
                print('Active career recovered:',pid,active,source,flush=True)
            if live is None or live.save!=source or getattr(self.server,'live_pid',None)!=pid:
                candidate=Career(str(self.server.career.game),save=source)
                self.server.live_career=candidate
                self.server.live_pid=pid
                if live is not None:retire_preview(live,candidate)
            return self.server.live_career
    def do_GET(self):
        path=urlparse(self.path).path
        routes={'/inicio':'home.html','/central':'central.html','/preview/save':'save.html'}
        if path in routes:
            query=urlparse(self.path).query
            self.path='/'+routes[path]+('?' + query if query else '')
            return super().do_GET()
        if path=='/api/career':
            try:return self.json(self.career_source().context())
            except Exception as error:
                traceback.print_exc();return self.json({'error':str(error)},500)
        if path=='/api/health':return self.json({'service':'fifa-friends-career-preview'})
        if path.startswith('/api/rooms/'):
            try:
                club,kind=path.split('/')[3:];pose={'press':301,'locker':302,'gym':303,'training':304}[kind]
                return self.json(self.career_source().pose(int(club),-3,pose,model=True))
            except Exception as error:return self.json({'error':str(error)},500)
        if path.startswith('/api/teams/'):
            try:
                club,mode,pose=path.split('/')[3:];return self.json(self.career_source().pose(int(club),-2 if mode=='squad' else -1,int(pose),model=True))
            except Exception as error:traceback.print_exc();return self.json({'error':str(error)},500)
        if path.startswith(('/api/players/','/api/models/')):
            try:
                club,player,pose=map(int,path.split('/')[3:])
                return self.json(self.career_source().pose(club,player,pose,model=path.startswith('/api/models/')))
            except Exception as error:traceback.print_exc();return self.json({'error':str(error)},500)
        if path.startswith('/api/clubs/'):
            try:
                result=self.career_source().get(int(path.removeprefix('/api/clubs/')),render='metadata=1' not in urlparse(self.path).query)
                def assets(value):
                    if isinstance(value,dict):return {k:assets(v) for k,v in value.items()}
                    if isinstance(value,list):return [assets(v) for v in value]
                    if isinstance(value,str) and value.startswith(('assets/','crests/','icons/')):return 'http://127.0.0.1:8876/'+value
                    return value
                return self.json(assets(result))
            except Exception as error:
                traceback.print_exc();return self.json({'error':str(error)},500)
        return super().do_GET()
    def json(self,value,status=200):
        def asset_url(item):
            if isinstance(item,str) and item.startswith('assets/runtime-cache/'):
                return 'http://127.0.0.1:8876/'+item
            if isinstance(item,dict):return {key:asset_url(entry) for key,entry in item.items()}
            if isinstance(item,list):return [asset_url(entry) for entry in item]
            return item
        value=asset_url(value)
        if isinstance(value,dict) and value.get('saveRevision'):
            value['saveRevision']+='-assets1'
        data=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--game-root');args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',8876),Handler)
    purge_expired_generated()
    server.career=Career(args.game_root)
    def expire():
        while True:
            time.sleep(3600)
            careers=[server.career]+([server.live_career] if hasattr(server,'live_career') else [])
            if any(c.pending for c in careers):continue
            purge_expired_generated()
    Thread(target=expire,daemon=True).start()
    server.serve_forever()
