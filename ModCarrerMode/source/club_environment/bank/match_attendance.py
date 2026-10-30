"""Per-fixture attendance: prefer the crowd mod's observed decision.

Never reuse today's live percentage for an already completed, different game.
Unobserved simulated fixtures use a labelled, deterministic reconstruction
from pre-match results and the crowd mod's configurable weights.
"""
from pathlib import Path
import configparser,ctypes,json,math

WEIGHTS=dict(base=.10,team_reputation=.30,opponent_reputation=.08,
 league_position=.12,recent_form=.06,last_results=.07,match_importance=.10,
 league_reputation=.12,competition_prestige=.10,rivalry=.08,
 escape_opportunity=.08,relegation_penalty=.10,low_reputation_penalty=.12,
 semifinal_bonus=.28,final_bonus=.38,last_round_bonus=.14,
 regular_match_base_limit_percent=30,elite_prestige_limit_bonus_percent=40,
 bad_form_limit_penalty_percent=20,rivalry_limit_bonus_percent=12,
 semifinal_maximum_percent=82,last_round_maximum_percent=78,
 final_minimum_percent=90,minimum_dynamic_percent=9,maximum_dynamic_percent=90)

def config(game):
 parser=configparser.ConfigParser(interpolation=None,strict=False)
 for path in (Path(game)/'ModCarrerMode/config/crowd.ini',Path(game)/'ModCarrerMode/crowd.ini'):
  try:
   blob=path.read_bytes()
   try:text=blob.decode('utf-8-sig')
   except UnicodeDecodeError:text=blob.decode('cp1252')
   parser.read_string(text);break
  except (OSError,configparser.Error):continue
 def number(section,key,default):
  try:
   value=float(parser.get(section,key).split(';',1)[0].strip())
   return value if math.isfinite(value) and 0<=value<=100 else default
  except (configparser.Error,ValueError):return default
 weights={k:number('crowd_weights',k,v) for k,v in WEIGHTS.items()}
 return dict(automatic=bool(number('crowd','automatic_dynamic_controller',1)),
  static=int(number('crowd','static_factor_percent',-1)),weights=weights)

def key(season,match):
 return ':'.join(str(v) for v in (season,match['root'],match['id'],match['home'],match['away']))

def validated_shared(row,pid,home,away,now):
 age=(now-row.heartbeat)&0xffffffff
 if (row.game_pid!=pid or not row.owner_pid or age>3000 or row.phase not in (1,2)
     or row.home_id!=home or row.away_id!=away or row.command<0 or row.ack!=row.command
     or row.status not in (2,3) or not 0<=row.current_percent<=100):return None
 return dict(percent=row.current_percent,source='crowd_match_applied',actual=True)

def shared_percent(pid,home,away):
 """Read only an existing, acknowledged, current-match shared mapping."""
 try:
  from server16_py.crowd_control import CrowdShared,MAPPING_NAME
  from ctypes import wintypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  kernel.OpenFileMappingW.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.LPCWSTR];kernel.OpenFileMappingW.restype=wintypes.HANDLE
  kernel.MapViewOfFile.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t];kernel.MapViewOfFile.restype=ctypes.c_void_p
  kernel.UnmapViewOfFile.argtypes=[ctypes.c_void_p];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
  handle=kernel.OpenFileMappingW(4,False,MAPPING_NAME)
  if not handle:return None
  address=None
  try:
   address=kernel.MapViewOfFile(handle,4,0,0,ctypes.sizeof(CrowdShared))
   if not address:return None
   raw=ctypes.string_at(address,ctypes.sizeof(CrowdShared));row=CrowdShared.from_buffer_copy(raw)
   if raw!=ctypes.string_at(address,ctypes.sizeof(CrowdShared)):return None
   return validated_shared(row,pid,home,away,kernel.GetTickCount())
  finally:
   if address:kernel.UnmapViewOfFile(address)
   kernel.CloseHandle(handle)
 except (OSError,ImportError,AttributeError):return None

def observe(game,save,live,*,pid,created=None):
 """Bind a live crowd value to one verified upcoming fixture in this save."""
 try:
  snap=json.loads((Path(game)/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text(encoding='utf8'))
  if (snap.get('schema')!=3 or snap.get('pid')!=pid or snap.get('club')!=live['club']
      or snap.get('date')!=live['date'] or Path(snap.get('savePath','')).resolve()!=Path(save).resolve()
      or created is not None and snap.get('processCreated100ns')!=created):return None
  candidates=[f for f in snap.get('fixtures',[]) if len(f)>=10 and live['club'] in f[5:7]
              and f[5]>0 and f[6]>0 and f[3]>=live['date'] and not f[9]]
  if not candidates:return None
  fixture=min(candidates,key=lambda f:(f[3],f[4],f[0]))
  nodes={n[0]:n for n in snap.get('nodes',[]) if len(n)>=4};at=fixture[1];seen=set()
  while at in nodes and at not in seen and nodes[at][2]!=3:seen.add(at);at=nodes[at][1]
  if at not in nodes or nodes[at][2]!=3:return None
  reading=shared_percent(pid,fixture[5],fixture[6])
  if reading is None:
   cfg=config(game);percent=cfg['static']
   if not 0<=percent<=100:return None
   # The automatic controller's INI is a global last value, not a fixture
   # record. It can still describe yesterday's opponent during a fast skip.
   # Unobserved simulations need their own pre-match estimate.
   if cfg['automatic']:return None
   else:reading=dict(percent=percent,source='crowd_manual',actual=False)
  return dict(id=fixture[0],root=at,asset=nodes[at][3],date=fixture[3],home=fixture[5],away=fixture[6],
              observed_date=live['date'],**reading)
 except (OSError,ValueError,KeyError,TypeError):return None


def clamp(value,lo=0.,hi=1.):return max(lo,min(hi,value))

def reconstruct(match,club,fixtures,teams,league_level,*,weights=None,rivals=()):
 """Estimated only: inputs stop BEFORE this fixture, never use its result."""
 w=dict(WEIGHTS);w.update(weights or {});opponent=match['away'] if match['home']==club else match['home']
 def reputation(ident):
  team=teams.get(ident,{})
  return clamp((int(team.get('domesticprestige') or 0)+int(team.get('internationalprestige') or 0))/40)
 rep=reputation(club);opp=reputation(opponent);league=clamp(1-(max(1,league_level)-1)*.7/6)
 season_start=match.get('season',match['date']//10000*10000+101)
 valid=[m for m in fixtures if m.get('played') and season_start<=m['date']<match['date']
           and type(m.get('homeScore')) is int and type(m.get('awayScore')) is int
           and 0<=m['homeScore']<100 and 0<=m['awayScore']<100]
 previous=[m for m in valid if club in (m['home'],m['away'])]
 previous.sort(key=lambda m:(m['date'],m['id']),reverse=True);recent=previous[:5]
 results=[(m['homeScore']-m['awayScore'])*(1 if m['home']==club else -1) for m in recent]
 form=sum(3 if r>0 else 1 if r==0 else 0 for r in results)/(3*len(results)) if results else .5
 momentum=.5
 if results:
  sign=1 if results[0]>0 else -1 if results[0]<0 else 0
  streak=0
  for result in results:
   if not sign or (1 if result>0 else -1 if result<0 else 0)!=sign:break
   streak+=1
  momentum=clamp(.5+.12*sign+(.1 if abs(results[0])>=3 else .05 if abs(results[0])==2 else 0)*sign+
                 (min(.18,.06*streak)*sign if streak>=2 else 0))
 rivals=set(tuple(sorted(p)) for p in rivals);rivalry=1. if tuple(sorted((club,opponent))) in rivals else 0.
 # Rebuild this competition's table BEFORE the match, rather than using the
 # final table at the end of a multi-day calendar jump (look-ahead bias).
 participants={t for m in fixtures if m['root']==match['root'] for t in (m['home'],m['away'])}
 table={t:[0,0,0] for t in participants}
 for m in valid:
  if m['root']!=match['root']:continue
  h,a=m['homeScore'],m['awayScore']
  for t,goals,other in ((m['home'],h,a),(m['away'],a,h)):
   row=table.setdefault(t,[0,0,0]);row[0]+=3 if goals>other else 1 if goals==other else 0;row[1]+=goals-other;row[2]+=1
 own=table.get(club,[0,0,0]);size=max(2,len(table));rank=1+sum((v[0],v[1])>(own[0],own[1]) for v in table.values())
 position=1-(rank-1)/(size-1);progress=clamp(own[2]/max(1,2*(size-1)))
 stage=match.get('stageKind',0);semi=stage==8;final=stage==10
 danger_slots=4 if size>8 else 2;danger_start=size-danger_slots+1
 danger=clamp((rank-(size-danger_slots-2))/max(1,danger_slots+2))
 ordered=sorted(table.values(),reverse=True);escape=0.
 if rank>=danger_start and danger_start>=2 and len(ordered)>=danger_start-1:
  gap=max(0,ordered[danger_start-2][0]-own[0]);escape=(1-clamp(gap/6))*clamp((progress-.35)/.65)
 importance=clamp(.2+.15*league+.25*rivalry+(.35*progress if rank<=3 or danger else 0)+.2*escape+(.1 if stage not in (0,2) else 0))
 competition=clamp((rep+opp)/2);factor=(w['base']+w['team_reputation']*rep+w['opponent_reputation']*opp+
  w['league_position']*progress*position+w['recent_form']*form+w['last_results']*momentum+
  w['match_importance']*importance+w['league_reputation']*league+w['competition_prestige']*competition+
  w['rivalry']*rivalry+w['escape_opportunity']*rep*escape-w['relegation_penalty']*(1-rep)*danger*progress-
  w['low_reputation_penalty']*(1-rep)*(1-max(league,competition)))
 cap=w['regular_match_base_limit_percent']+w['elite_prestige_limit_bonus_percent']*max(rep,league*.7,competition,opp*.7)
 cap-=w['bad_form_limit_penalty_percent']*max(0,1-form*2);cap+=w['rivalry_limit_bonus_percent']*rivalry
 low=w['minimum_dynamic_percent'];high=w['maximum_dynamic_percent']
 if progress>=.9:factor+=w['last_round_bonus'];cap=max(cap,w['last_round_maximum_percent'])
 if final:factor+=w['final_bonus'];low=max(low,w['final_minimum_percent']);cap=high
 elif semi:factor+=w['semifinal_bonus'];cap=w['semifinal_maximum_percent']
 low=clamp(low,0,100);high=clamp(max(low,high),low,100)
 percent=int(clamp(factor*100,low,min(high,max(low,cap)))+.5)
 return dict(percent=percent,source='crowd_reconstructed',actual=False)
