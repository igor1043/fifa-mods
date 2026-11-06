"""Validate one explicit profile click against the current published market."""
from pathlib import Path

RESUME=('tab','page','country','league','movementCountry','movementLeague','month','hirePage','movePage','nation','focus')

def read(path,observed,model,now):
 fields=dict(line.split('=',1) for line in Path(path).read_text(encoding='ascii').splitlines() if '=' in line)
 if fields.get('schema')!='1':raise ValueError('Versão de pedido incompatível')
 saved=observed['save'];profile=observed['profile'];captured=int(fields['captured_tick'])
 if any(int(fields[k])!=v for k,v in dict(pid=saved['pid'],created=saved['process_created_100ns'],epoch=profile.get('context_epoch',0),club=profile['club_id'],date=observed['date']).items()):raise ValueError('Perfil de outra sessão/data')
 if int(fields['context'],16)!=profile['context_address'] or not 0<=now-captured<=30000:raise ValueError('Pedido de perfil expirado')
 parts=fields['wire'].split('|')
 if len(parts)!=15 or parts[0]!='S16MGRP1' or parts[-1]!='END' or parts[1]!=model.get('profileToken'):raise ValueError('Catálogo de perfil substituído')
 values=[int(v) for v in parts[2:-1]];person=values[0];resume=dict(zip(RESUME,values[1:]))
 if person< -1 or person>=len(model['people']):raise ValueError('Técnico fora do catálogo')
 if any(v<0 or v>200000 for v in resume.values()) or resume['tab']>4:raise ValueError('Navegação inválida')
 resume.update(profile=person>=0,person=max(0,person),profileTab=0,profileVenue=0,historyPage=0)
 return dict(identity=(captured,fields['wire']),person=person,coach=model['people'][person]['id'] if person>=0 else None,resume=resume)
