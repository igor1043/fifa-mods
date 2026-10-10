import sys,struct,json,hashlib,math
from pathlib import Path
sys.path.insert(0,r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster\vendor\rx3tools')
from rx3 import Rx3,read_model,FORMAT,VERTEX
root=Path(r'U:\fifa 16\ModCarrerMode\source\mascot_arm_repair');root.mkdir(exist_ok=True)
baseline=root/'before_model.rx3'
if not baseline.exists():baseline.write_bytes(Path(r'U:\fifa 16\data\sceneassets\mascot\1035\model.rx3').read_bytes())
raw=baseline.read_bytes();rx=Rx3(raw);parts,bones=read_model(rx);p=parts[0];n=len(p['positions'])//3
js=p['joints'][:];ws=p['weights'][:];changed=[];counts={1:0,-1:0}
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def project(v,a,b):
 d=[b[k]-a[k] for k in range(3)];l=dist(a,b);t=max(0,min(1,sum((v[k]-a[k])*d[k] for k in range(3))/(l*l)))
 return t*l,dist(v,[a[k]+t*d[k] for k in range(3)])
for i in range(n):
 v=p['positions'][i*3:i*3+3];x,y,z=v;side=1 if x>=0 else -1;ids=[16,17,18,19] if side==1 else [21,22,23,24]
 old={}
 for j,w in zip(js[i*4:i*4+4],ws[i*4:i*4+4]):old[j]=old.get(j,0)+w/255
 if y<74 or y>139 or old.get(14,0)>.25:continue
 arm=sum(old.get(j,0) for j in ids)
 if not ((abs(x)>=29 and y>=74) or (arm>.08 and abs(x)>=16 and y>=108)):continue
 a,b,c=[bones[j][12:15] for j in ids[1:]];l1=dist(a,b);l2=dist(b,c);s1,d1=project(v,a,b);s2,d2=project(v,b,c);s=s1 if d1<=d2 else l1+s2
 upper=1-smooth(l1-8,l1+9,s);hand=smooth(l1+l2-19,l1+l2-7,s);fore=max(0,1-upper-hand)
 shoulder=(1-smooth(17,30,abs(x)))*.35
 body=(1-smooth(18,29,abs(x)))*max(0,1-arm)
 values={ids[1]:upper*(1-shoulder),ids[2]:fore,ids[3]:hand,ids[0]:upper*shoulder}
 values={j:w*(1-body) for j,w in values.items()}
 values[12]=body
 top=sorted([(j,w) for j,w in values.items() if w>1e-6],key=lambda t:-t[1])[:4];total=sum(w for j,w in top);ww=[round(w/total*255) for j,w in top];ww[0]+=255-sum(ww);jj=[j for j,w in top]
 jj+= [jj[0]]*(4-len(jj));ww+=[0]*(4-len(ww))
 if jj!=js[i*4:i*4+4] or ww!=ws[i*4:i*4+4]:changed.append(i);counts[side]+=1
 js[i*4:i*4+4]=jj;ws[i*4:i*4+4]=ww
fields={}
for t in rx.get(FORMAT)[0][16:].split(b'\0')[0].decode().split():
 sem,off,_,_,fmt=t.split(':');fields[sem]=(int(off,16),fmt)
if fields['i0'][1]!='4u8' or fields['w0'][1]!='4u8n':raise ValueError('unexpected vertex layout')
entries=[struct.unpack_from('<4I',raw,16+16*i) for i in range(struct.unpack_from('<I',raw,12)[0])];vb=next(e for e in entries if e[0]==VERTEX);stride=struct.unpack_from('<I',raw,vb[1]+8)[0];out=bytearray(raw)
for i in changed:
 at=vb[1]+16+i*stride;out[at+fields['i0'][0]:at+fields['i0'][0]+4]=bytes(js[i*4:i*4+4]);out[at+fields['w0'][0]:at+fields['w0'][0]+4]=bytes(ws[i*4:i*4+4])
used=sorted({j for j,w in zip(js,ws) if w});entry=next(e for e in entries if e[0]==0x0F3861A2);remap=bytearray(528);struct.pack_into('<I',remap,0,528);remap[4]=len(used)
for compact,j in enumerate(used):remap[16+j]=compact;remap[272+compact]=j
out[entry[1]:entry[1]+528]=remap
candidate=root/'candidate';candidate.mkdir(exist_ok=True)
for name in ['model.rx3','model_animated.rx3']:(candidate/name).write_bytes(out)
report={'club':1035,'changedVertices':len(changed),'positiveArm':counts[1],'negativeArm':counts[-1],'meshUvBindUnchanged':True,'method':'same-side anatomical chain projection, smooth elbow and wrist transitions, torso blend at shoulder only','sha256':hashlib.sha256(out).hexdigest()}
(root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
