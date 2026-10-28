"""Build the tournament tree from actual CompData advancement links."""
from collections import defaultdict

def build(rounds,formats,links):
 stages={r['stage']:i for i,r in enumerate(rounds)};nodes={};edges=[];previous=defaultdict(list)
 for r in rounds:
  meta=formats.get(r['stage'],{})
  for gid in meta.get('groups',[]):
   tie=next((j for j,t in enumerate(r['ties']) if any(m.get('group')==gid for m in t['legs'])),-1)
   nodes[gid]=dict(id=gid,round=stages[r['stage']],tie=tie,x=0,y=0)
 for source,rank,destination,slot in links:
  if source in nodes and destination in nodes:
   edges.append(dict(source=source,destination=destination,rank=rank,slot=slot))
   if rank==1:previous[destination].append((slot,source))
 for value in previous.values():value.sort()
 finals=[n for n in nodes if rounds[nodes[n]['round']]['kind']==10]
 final=max(finals,key=lambda n:(nodes[n]['round'],n)) if finals else None
 done=set();counts={}
 def leaves(n,seen=None):
  seen=set() if seen is None else seen
  if n in counts:return counts[n]
  if n in seen:return 1
  seen=seen|{n};result=sum(leaves(p,seen) for _,p in previous[n]) or 1;counts[n]=result;return result
 def place(n,side,depth,start,span):
  if n in done:return
  done.add(n);nodes[n].update(x=side*depth*340,y=start+span/2)
  parents=previous[n];total=sum(leaves(p) for _,p in parents) or 1;at=start
  for _,p in parents:
   part=span*leaves(p)/total;place(p,side,depth+1,at,part);at+=part
 if final is not None:
  done.add(final);nodes[final].update(x=0,y=0)
  parents=previous[final]
  for i,(_,p) in enumerate(parents):
   span=leaves(p)*148;place(p,-1 if i%2==0 else 1,1,-span/2,span)
 # Third-place games and disconnected preliminary draws remain visible, but
 # are never connected to a fictitious winner. Their real links are retained.
 extra=[n for n in nodes if n not in done];by_round=defaultdict(list)
 for n in extra:by_round[nodes[n]['round']].append(n)
 bottom=max((v['y'] for v in nodes.values() if v['id'] in done),default=0)+260
 for phase,items in sorted(by_round.items()):
  for i,n in enumerate(items):
   side=-1 if i<len(items)/2 else 1;depth=max(1,len(rounds)-1-phase);nodes[n].update(x=side*depth*340,y=bottom+(i%max(1,(len(items)+1)//2))*148)
 if not nodes:return dict(nodes=[],edges=[],final=0)
 return dict(nodes=list(nodes.values()),edges=edges,final=final or 0)
