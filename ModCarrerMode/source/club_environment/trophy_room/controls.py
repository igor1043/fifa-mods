"""One footer layout for the native drawing and the APT mouse hit targets."""
LEFT,TOP,COLUMN,ROW,WIDTH,HEIGHT=60,838,370,29,350,26
# mode: list, tour, inspection, free camera, loading. -1 is Back, -2 a hint.
MODES=(
 (('A / Enter','Ver taça em 3D',4),('B / Esc','Voltar',-1),('LS / Setas','Navegar',-2),('LB / RB','Clube / treinador',5),('LT / G','Galeria',6),('RT / H','Sala 3D',7),('Y / PgDn','Próxima página',0)),
 (('A / Enter','Detalhes da taça',4),('B / Esc','Galeria',-1),('Y / F1','Próxima taça',0),('X / F2','Câmera livre',1),('LT / G','Galeria',6),('RT / H','Sala 3D',7)),
 (('B / Esc','Voltar',-1),('RS / Mouse','Rotacionar',-2),('LT / RT','Zoom',-2),('LS / Setas','Histórico',-2),('Y / F1','Próxima taça',0)),
 (('B / Esc','Galeria',-1),('LS / WASD','Andar',-2),('RS / Mouse','Olhar',-2),('LB / RB','Descer / subir',-2),('X / F2','Passeio',1),('LT / G','Galeria',6),('RT / H','Sala 3D',7)),
 (('B / Esc','Voltar',-1),('LT / G','Galeria',6),('RT / H','Sala 3D',7)),
)


def cpp_header():
    import json
    quote=lambda s:json.dumps(s,ensure_ascii=False)
    lines=['// Generated from trophy_room/controls.py.','\n#pragma once','namespace trophy_controls {',
           f'constexpr float left={LEFT},top={TOP},column={COLUMN},row={ROW},width={WIDTH},height={HEIGHT};',
           'struct Item {const wchar_t* key;const wchar_t* label;int action;};']
    for mode,items in enumerate(MODES):
        values=','.join('{L'+quote(key)+',L'+quote(label)+','+str(action)+'}' for key,label,action in items)
        lines.append(f'constexpr Item mode{mode}[]={{'+values+'};')
    lines.extend(['inline const Item* items(unsigned mode,unsigned&count){','switch(mode){'])
    for mode,items in enumerate(MODES):lines.append(f'case {mode}:count={len(items)};return mode{mode};')
    lines.extend(['default:count=0;return nullptr;}}','}'])
    return '\n'.join(lines)+'\n'
