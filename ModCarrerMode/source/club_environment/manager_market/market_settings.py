"""User preferences and a career-scoped, snapshot-safe review cursor."""
import json
import os
from datetime import date
from pathlib import Path

DEFAULTS = dict(enabled=True, cadence=1)
CADENCES = (1, 7, 30)
LABELS = ('Diário', 'Semanal', 'Mensal')

def normalized(value):
    if not isinstance(value,dict):raise ValueError('Preferências inválidas')
    if type(value.get('enabled')) not in (bool, int) or value['enabled'] not in (0, 1):
        raise ValueError('Ativação inválida')
    if type(value.get('cadence')) is not int or value['cadence'] not in CADENCES:
        raise ValueError('Frequência inválida')
    return dict(enabled=bool(value['enabled']), cadence=value['cadence'])

def read(path):
    try:
        return normalized(json.loads(Path(path).read_text(encoding='utf8')))
    except FileNotFoundError:
        return dict(DEFAULTS)

def write(path, value):
    value = normalized(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + str(os.getpid()) + '.new')
    temp.write_text(json.dumps(dict(schema=1, **value), ensure_ascii=False) + '\n', encoding='utf8')
    os.replace(temp, path)
    return value

def request(path, observed, model, now):
    fields = dict(line.split('=', 1) for line in Path(path).read_text(encoding='ascii').splitlines() if '=' in line)
    saved, profile = observed['save'], observed['profile']
    if fields.get('schema') != '1':
        raise ValueError('Pedido incompatível')
    for k, expected in dict(pid=saved['pid'], created=saved['process_created_100ns'], epoch=profile.get('context_epoch', 0), club=profile['club_id'], date=observed['date']).items():
        if int(fields[k]) != expected:
            raise ValueError('Configuração de outra sessão')
    if int(fields['context'], 16) != profile['context_address'] or not 0 <= now-int(fields['captured_tick']) <= 30000:
        raise ValueError('Pedido de configuração expirado')
    parts = fields['wire'].split('|')
    if len(parts) != 6 or parts[0] != 'S16MGRS1' or parts[-1] != 'END' or parts[1] != model.get('profileToken'):
        raise ValueError('Tela de configuração substituída')
    if parts[2] not in ('0', '1') or parts[3] not in ('0', '1', '2') or not parts[4].isdigit() or len(parts[4]) > 9:
        raise ValueError('Opção de configuração inválida')
    return dict(identity=(int(fields['captured_tick']), fields['wire']), value=dict(enabled=parts[2]=='1', cadence=CADENCES[int(parts[3])]))

def review_dates(market, dates, policy):
    """Only decisions are batched; dated football evidence is never dropped."""
    dates = sorted(set(dates))
    today = dates[-1]
    cadence = int(policy.get('review_cadence', 1))
    enabled = bool(policy['enabled'])
    row = market.db.execute('SELECT last_review,cadence,enabled FROM market_cycles WHERE branch=?', (market.branch,)).fetchone()
    last = row[0] if row else market.info()['game_date']
    if not enabled:
        selected = set()
    elif cadence == 1:
        selected = set(dates)  # Exact legacy daily behavior, including richer same-day evidence.
    else:
        def bucket(value):
            if cadence == 30:
                return value//10000*12 + value//100%100
            at = date(value//10000, value//100%100, value%100)
            return (at.toordinal()-1)//7
        selected = set()
        for value in dates:
            if bucket(value) > bucket(last):
                selected.add(value)
                last = value
    market.db.execute('INSERT OR REPLACE INTO market_cycles VALUES(?,0,?,?,?)', (market.branch, max(selected) if selected else today if not enabled else last, cadence, int(enabled)))
    return selected
