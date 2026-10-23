import portable_paths as portable
"""Scene slots are backed only by real, linked players in this career."""
def roster_order(players,links,favourite=(),limit=35):
    candidates=list(favourite)+sorted(links,key=lambda p:(links[p].value('jerseynumber'),p))
    return [p for p in dict.fromkeys(candidates) if p>0 and p in players and p in links][:limit]

def scene_catalog(context,roster):
    result=[{'label':'Visão geral do vestiário'}]
    order=list(range(34,11,-2))+list(range(12))+list(range(13,35,2))
    for i in order:
        if i<len(roster):
            p=roster[i];result.append({'label':f"Camisa {p['number']} · {p['name'] or 'Jogador'}",'locker':i,'player':p['id']})
    result.append({'label':'Quadro da próxima partida'})
    for p in context['focus']:result.append({'label':f"Destaque camisa {p['number']} · {p['name'] or 'Jogador'}"})
    result.extend({'label':name} for name in ('Entrada e lateral direita','Armários à direita','Fundo à direita','Panorama dos armários','Fundo à esquerda','Armários à esquerda','Entrada e lateral esquerda'))
    import json
    from pathlib import Path
    medical=portable.ROOM/'runtime/medical_room_r57.json'
    if medical.exists():result.extend({'label':s['label']} for s in json.loads(medical.read_text(encoding='utf8'))['scenes'])
    return [dict(id=i,**r) for i,r in enumerate(result)]
