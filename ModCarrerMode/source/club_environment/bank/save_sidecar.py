"""Portable SQLite ledger next to DATA. Native FIFA saves are only read."""
from pathlib import Path
import hashlib,json,sqlite3
from contextlib import contextmanager
from loans import BANK_DEFAULTS,PREVIOUS_RATES

NAME='server16_loans.sqlite3'
SCHEMA='''
CREATE TABLE IF NOT EXISTS bank_catalog(bank_id INTEGER PRIMARY KEY,slug TEXT UNIQUE NOT NULL,name TEXT NOT NULL,rate_bps INTEGER NOT NULL CHECK(rate_bps BETWEEN 10 AND 1000));
CREATE TABLE IF NOT EXISTS snapshots(save_hash TEXT PRIMARY KEY,club INTEGER NOT NULL,game_date INTEGER NOT NULL,budget INTEGER NOT NULL,native_io_tick INTEGER NOT NULL,state_json TEXT NOT NULL,notifications_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS applications(save_hash TEXT,request_id TEXT,submitted_date INTEGER,response_date INTEGER,status TEXT,payload_json TEXT,PRIMARY KEY(save_hash,request_id));
CREATE TABLE IF NOT EXISTS contracts(save_hash TEXT,contract_id TEXT,bank_id INTEGER,principal INTEGER,rate_bps INTEGER,paid INTEGER,months INTEGER,PRIMARY KEY(save_hash,contract_id));
CREATE TABLE IF NOT EXISTS installments(save_hash TEXT,contract_id TEXT,number INTEGER,due_date INTEGER,amount INTEGER,paid_date INTEGER,method TEXT,PRIMARY KEY(save_hash,contract_id,number));
CREATE TABLE IF NOT EXISTS operations(save_hash TEXT,operation_id TEXT,kind TEXT,amount INTEGER,game_date INTEGER,applied INTEGER,PRIMARY KEY(save_hash,operation_id));
CREATE TABLE IF NOT EXISTS live_operations(operation_key TEXT PRIMARY KEY,session TEXT,reason TEXT,status TEXT,game_date INTEGER,budget_before INTEGER,budget_after INTEGER,delta INTEGER,journal_json TEXT);
CREATE TABLE IF NOT EXISTS club_ledgers(save_hash TEXT,club INTEGER,state_json TEXT NOT NULL,notifications_json TEXT NOT NULL,PRIMARY KEY(save_hash,club));
CREATE TABLE IF NOT EXISTS session_clubs(session TEXT,save_hash TEXT,club INTEGER,native_io_tick INTEGER,state_json TEXT NOT NULL,notifications_json TEXT NOT NULL,PRIMARY KEY(session,save_hash,club));
CREATE TABLE IF NOT EXISTS loan_requests(request_id TEXT PRIMARY KEY,session TEXT,save_hash TEXT,club INTEGER,submitted_date INTEGER NOT NULL,response_date INTEGER NOT NULL,registered_date INTEGER,status TEXT,decided_date INTEGER,credit_applied INTEGER NOT NULL,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS loan_outbox(notice_id TEXT PRIMARY KEY,request_id TEXT,session TEXT,save_hash TEXT,club INTEGER,kind TEXT,due_date INTEGER,delivered INTEGER,delivered_date INTEGER,payload_json TEXT NOT NULL);
PRAGMA user_version=3;
'''

def path_for(save):return Path(save).parent/NAME

@contextmanager
def connection(save):
    path=path_for(save);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=3)
    try:
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0,1,2,3):raise ValueError('Versão do histórico financeiro não suportada')
        if version<3:
            migration=SCHEMA.replace('PRAGMA user_version=3;', 'INSERT OR IGNORE INTO club_ledgers SELECT save_hash,club,state_json,notifications_json FROM snapshots; PRAGMA user_version=3; COMMIT;')
            db.executescript('BEGIN IMMEDIATE;'+migration)
        present={r[0] for r in db.execute('SELECT bank_id FROM bank_catalog')}
        missing=[(i,b['id'],b['name'],b['rate_bps']) for i,b in enumerate(BANK_DEFAULTS) if i not in present]
        if missing:db.executemany('INSERT INTO bank_catalog VALUES(?,?,?,?)',missing)
        # One-time calibration of unedited prototype defaults. Existing quotes,
        # contracts and manually configured SQL rates remain untouched.
        db.execute('CREATE TABLE IF NOT EXISTS bank_catalog_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        if not db.execute("SELECT 1 FROM bank_catalog_settings WHERE key='reference_rates_20261024'").fetchone():
            for bank in BANK_DEFAULTS:
                previous=PREVIOUS_RATES.get(bank['id'])
                if previous is not None:db.execute('UPDATE bank_catalog SET rate_bps=? WHERE slug=? AND rate_bps=?',(bank['rate_bps'],bank['id'],previous))
            db.execute("INSERT INTO bank_catalog_settings VALUES('reference_rates_20261024','1')")
        with db:yield db
    finally:db.close()

def bank_rows(save):
    with connection(save) as db:return db.execute('SELECT bank_id,slug,name,rate_bps FROM bank_catalog ORDER BY bank_id').fetchall()

def load_snapshot(save,digest,club):
    if not path_for(save).exists():return None
    with connection(save) as db:
        row=db.execute('SELECT club,state_json,notifications_json FROM snapshots WHERE save_hash=?',(digest,)).fetchone()
    if not row:return None
    if row[0]!=club:raise ValueError('Histórico financeiro pertence a outro clube')
    state=json.loads(row[1])
    if state['club']!=club:raise ValueError('Clube divergente no histórico financeiro')
    return dict(state=state,notifications=json.loads(row[2]))

def save_snapshot(save,saved,state,notifications,native_io,clubs=None):
    if native_io.get('operation')!='write' or native_io.get('complete_file')!='1':raise ValueError('Histórico exige uma gravação nativa completa')
    if state['club']!=saved['club']:raise ValueError('Clube divergente na gravação')
    # Verify the same file bytes used by the native-save observer. A foreign or
    # partially replaced DATA can never adopt the current unsaved ledger.
    if hashlib.sha256(Path(save).read_bytes()).hexdigest()!=saved['hash']:raise ValueError('Save mudou durante a gravação do histórico')
    digest=saved['hash'];encode=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True)
    with connection(save) as db:
        db.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?,?,?,?)',(digest,saved['club'],saved['date'],saved['budget'],int(native_io.get('access_tick_ms',0)),encode(state),encode(notifications)))
        ledgers=dict(clubs or {});ledgers[state['club']]=dict(state=state,notifications=notifications)
        db.execute('DELETE FROM club_ledgers WHERE save_hash=?',(digest,))
        for club,row in ledgers.items():
            if int(club)!=row['state']['club']:raise ValueError('Clube divergente no histórico da carreira')
            db.execute('INSERT INTO club_ledgers VALUES(?,?,?,?)',(digest,int(club),encode(row['state']),encode(row['notifications'])))
            write_requests(db,digest,'native-save',row['state'],row['notifications'])
        for table in ('applications','contracts','installments','operations'):db.execute('DELETE FROM '+table+' WHERE save_hash=?',(digest,))
        for row in state.get('applications',[]):
            db.execute('INSERT INTO applications VALUES(?,?,?,?,?,?)',(digest,row['id'],row['date'],row['decision_date'],row['status'],encode(row)))
        for c in state['contracts']:
            db.execute('INSERT INTO contracts VALUES(?,?,?,?,?,?,?)',(digest,c['id'],c['bank'],c['principal'],c['rate_bps'],c['paid'],c['months']))
            db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',(digest,c['id'],'credit',c['principal'],c['date'],1))
            for p in c['payments']:
                db.execute('INSERT INTO installments VALUES(?,?,?,?,?,?,?)',(digest,c['id'],p['number'],p['date'],p['amount'],p.get('paid_date'),p.get('method')))
                if p['number']<=c['paid']:
                    db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',(digest,c['id']+':'+str(p['number']),'installment',p['amount'],p['paid_date'],1))
    return path_for(save)

def write_journal(save,journal):
    before=journal['before'];events=journal.get('events',[])
    key=hashlib.sha256(json.dumps([journal['session'],journal['reason'],journal['native_io_tick'],events],sort_keys=True).encode()).hexdigest()
    with connection(save) as db:
        if journal.get('state_after') is not None:write_requests(db,journal.get('source_save_hash',''),journal['session'],journal['state_after'],[])
        db.execute('INSERT OR REPLACE INTO live_operations VALUES(?,?,?,?,?,?,?,?,?)',(key,journal['session'],journal['reason'],journal['status'],before['date'],before['budget'],journal['after_budget'],journal['after_budget']-before['budget'],json.dumps(journal,ensure_ascii=False,sort_keys=True)))


def load_clubs(save,digest):
    if not path_for(save).exists():return {}
    with connection(save) as db:
        rows=db.execute('SELECT club,state_json,notifications_json FROM club_ledgers WHERE save_hash=?',(digest,)).fetchall()
    return {club:dict(state=json.loads(state),notifications=json.loads(notices)) for club,state,notices in rows}


def save_session_club(save,digest,session,native_io_tick,state,notifications):
    """Same-process recovery only: never adopt unsaved money from another session."""
    with connection(save) as db:
        write_requests(db,digest,session,state,notifications)
        db.execute('INSERT OR REPLACE INTO session_clubs VALUES(?,?,?,?,?,?)',(session,digest,state['club'],native_io_tick,json.dumps(state,ensure_ascii=False),json.dumps(notifications,ensure_ascii=False)))


def load_session_clubs(save,digest,session,native_io):
    if not path_for(save).exists():return {}
    with connection(save) as db:
        rows=db.execute('SELECT club,native_io_tick,state_json,notifications_json FROM session_clubs WHERE session=? AND save_hash=?',(session,digest)).fetchall()
    tick=int(native_io.get('access_tick_ms',0)) if native_io.get('operation')=='read' else 0
    return {club:dict(state=json.loads(state),notifications=json.loads(notices)) for club,observed,state,notices in rows if tick<=observed}


def write_requests(db,digest,session,state,notifications):
    """Queryable live SQL rows; native-save/session snapshots remain authoritative."""
    encode=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True)
    for a in state.get('applications',[]):
        fixed=(a['date'],a['decision_date'])
        existing=db.execute('SELECT submitted_date,response_date FROM loan_requests WHERE request_id=?',(a['id'],)).fetchone()
        if existing is not None and tuple(existing)!=fixed:
            raise ValueError('As datas originais do pedido de empréstimo não podem mudar')
        db.execute('INSERT OR REPLACE INTO loan_requests VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (a['id'],session,digest,state['club'],*fixed,a.get('registered_date',a['date']),a['status'],a.get('decided_date'),
             int(a['status']=='approved' and any(c['id']==a['id'] for c in state['contracts'])),encode(a)))
    for n in notifications:
        if not {'id','request_id','club','due','delivered'}.issubset(n):continue
        db.execute('INSERT OR REPLACE INTO loan_outbox VALUES(?,?,?,?,?,?,?,?,?,?)',
            (n['id'],n['request_id'],session,digest,n['club'],n.get('kind','decision'),n['due'],int(n['delivered']),n.get('delivered_date'),encode(n)))
