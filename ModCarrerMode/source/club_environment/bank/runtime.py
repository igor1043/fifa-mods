import portable_paths as portable
"""Experimental bank bridge: native-screen requests, guarded budget, save snapshots.

Never edits DATA, INDEX, executable code, assets in RAM, camera, or input state.
Only an explicit request from the separate bank screen enables a 4-byte budget
publication. Scheduled debits require this same career and an idle hub page.
"""
from pathlib import Path
import argparse,ctypes,json,re,struct,sys,time,os,secrets,threading,queue
from ctypes import wintypes
import psutil
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
from server16_py.career_active_save import read_active_save
from server16_py.career_read import CareerRead
from loans import *
from build_screen import PAGE,NONCE
import loan_notifications
import save_sidecar
import club_finance

FINANCE_PAGE='game/screens/career/server16/ClubFinance'

GAME=portable.GAME
HERE=Path(__file__).resolve().parent
LOG=HERE/'runtime/bank_loans.log'
STATE=HERE/'runtime'
PATTERN=re.compile(r'S16BANK_V1\|'+NONCE+r'\|([0-9]{1,6})\|([0-2])\|([0-3])\|([0-2])\|END_S16BANK')


class Region(ctypes.Structure):
    _fields_=[('base',ctypes.c_void_p),('allocation',ctypes.c_void_p),('allocation_protect',wintypes.DWORD),
              ('partition',wintypes.WORD),('size',ctypes.c_size_t),('state',wintypes.DWORD),
              ('protect',wintypes.DWORD),('type',wintypes.DWORD)]


class RequestReader:
    """Continuous, read-only input discovery, independent of page and UI builds.

    This Python thread only calls ReadProcessMemory. Financial publication and
    all native FIFA APIs retain their existing owners and validation.
    """
    def __init__(self,process,base,nonce):
        self.process=process;self.base=base;self.nonce=nonce
        self.messages=queue.Queue();self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,name='bank-request-reader',daemon=True)
        self.thread.start()

    def run(self):
        memory=Memory();memory.process_id=self.process.pid
        memory.process_handle=memory.kernel32.OpenProcess(0x410,False,self.process.pid)
        memory.base_module=self.base
        try:
            if not memory.process_handle:raise OSError('FIFA não permite leitura dos pedidos')
            scanner=Bridge.__new__(Bridge);scanner.memory=memory;scanner.nonce=self.nonce;scanner.last_sequence=0
            while not self.stop.is_set() and self.process.is_running():
                for row in scanner.scan_bounded():
                    if row[0]>scanner.last_sequence:
                        scanner.last_sequence=row[0];self.messages.put(row)
                # Yield between bounded batches; never occupy a full CPU core
                # while the player stays in Central or advances the calendar.
                self.stop.wait(.08)
        except Exception as error:
            self.messages.put(error)
        finally:memory.close()

    def read(self):
        rows=[]
        while True:
            try:row=self.messages.get_nowait()
            except queue.Empty:return rows
            if isinstance(row,Exception):raise RuntimeError('Leitura dos pedidos interrompida: '+str(row))
            rows.append(row)

    def close(self):
        self.stop.set();self.thread.join(2)


def financial_page(page):
    # Both Central's advance and the calendar read the same verified native day.
    # Menu transitions/results wait until one of these stable front-end views.
    return page.casefold() in (PAGE.casefold(),FINANCE_PAGE.casefold(),'game/screens/fluxhub/fluxhub',
        'game/screens/misc/stadiumpan','game/screens/career/calendar')


def log(event,**fields):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('a',encoding='utf8') as stream:
        stream.write(json.dumps(dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**fields),ensure_ascii=False)+'\n')


def requests_in(data,nonce=NONCE):
    pattern=re.compile(r'S16BANK_V([234])\|'+re.escape(nonce)+r'\|([0-9]{1,9})\|([0-2])\|([0-9]{1,2})\|([0-9]{1,2})\|([0-9]{1,2})\|(?:(\d{8})\|)?(?:([A-Za-z0-9_:-]{1,160})\|)?END_S16BANK')
    found=set()
    for encoding in ('ascii','utf-16-le'):
        needle='S16BANK_V'.encode(encoding)
        start=data.find(needle)
        while start>=0:
            text=data[start:start+1024].decode(encoding,errors='ignore')
            match=pattern.match(text)
            if match:
                version,*values,submitted,target=match.groups()
                numbers=tuple(map(int,values))
                if not (numbers[2]<len(BANKS) and numbers[3]<len(AMOUNTS) and numbers[4]<len(TERMS)):
                    start=data.find(needle,start+len(needle));continue
                if version=='2' and submitted is None and target is None:found.add(numbers)
                elif version in ('3','4') and submitted is not None:
                    try:parse_date(int(submitted))
                    except ValueError:pass
                    else:
                        if version=='3' and target is None:found.add(numbers+(int(submitted),))
                        elif version=='4' and target and numbers[1] in (1,2) and target!='-':found.add(numbers+(int(submitted),target))
            start=data.find(needle,start+len(needle))
    return found


def read_direct_request(folder,*,pid,club,context,epoch,nonce):
    """Read the native click mailbox; never execute anything in FIFA."""
    try:
        path=Path(folder)/'native_request.tsv'
        if path.stat().st_size>2048:return []
        fields=dict(line.split('=',1) for line in path.read_text(encoding='ascii').splitlines() if '=' in line)
        if (fields.get('schema')!='1' or fields.get('pid')!=str(pid) or fields.get('club')!=str(club)
            or fields.get('context')!=f'{context:x}' or fields.get('epoch')!=str(epoch)):return []
        captured=int(fields['date']);parse_date(captured)
        found=requests_in(fields['wire'].encode('ascii'),nonce)
        # The native click day is authoritative, even if an APT view was old.
        return sorted(row[:5]+(captured,)+row[6:] for row in found if row[0]>0)
    except (OSError,UnicodeError,ValueError,KeyError):return []


def recover_pending(state,live,journal,session,native_io,save_hash=None):
    """Recover a recorded debt, never replay its budget write or a loaded save."""
    before=journal.get('before',{})
    if (journal.get('status')=='request_registered' and save_hash
            and journal.get('source_save_hash')==save_hash and before.get('club')==live['club']
            and journal['state_after']['last_date']<=live['date']):
        if (journal.get('session')==session and native_io.get('operation')=='read'
                and int(native_io.get('access_tick_ms',0))>journal.get('native_io_tick',0)):return state
        return journal['state_after']
    if (journal.get('session')!=session or before.get('address')!=live['address']
            or before.get('club')!=live['club'] or journal.get('status')=='native_saved'):
        return state
    if (native_io.get('operation')=='read'
            and int(native_io.get('access_tick_ms',0))>journal.get('native_io_tick',0)):
        return state
    if journal.get('status')=='applied_in_ram_awaiting_native_save' or live['budget']==journal.get('after_budget'):
        return journal['state_after']
    if live['budget']!=before.get('budget'):
        raise RuntimeError('Operação financeira pendente sem confirmação; consulte o diagnóstico')
    return state


def career_clubs(save,saved,live,profile,session,native_io):
    """The selected RAM user is authoritative after a job change in this career."""
    if saved['userid']!=profile['userid'] or live['club']!=profile['club_id']:
        raise RuntimeError('Usuário da carreira diverge da RAM')
    if live['date']<saved['date']:raise RuntimeError('Aguardando a data da carreira terminar de carregar')
    rows=save_sidecar.load_clubs(save['path'],saved['hash'])
    rows.update(save_sidecar.load_session_clubs(save['path'],saved['hash'],session,native_io))
    # Migrate the preceding club's confirmed JSON ledger as well. It must never
    # become the new club's debt, or disappear when the next save is written.
    previous=saved['club']
    if previous not in rows:
        scope=fingerprint((save['path'].casefold()+'|'+str(previous)).encode())[:20]
        folder=STATE/scope;initial=folder/'snapshots'/(saved['hash']+'.json')
        if initial.exists():
            state=json.loads(initial.read_text(encoding='utf8'))['state']
            notices=folder/'notifications.json'
            rows[previous]=dict(state=state,notifications=json.loads(notices.read_text(encoding='utf8')) if notices.exists() else [])
        pending=folder/'pending.json'
        if pending.exists():
            journal=json.loads(pending.read_text(encoding='utf8'));tick=int(native_io.get('access_tick_ms',0))
            valid=(journal.get('session')==session and journal.get('before',{}).get('club')==previous
                and journal.get('status') in ('request_registered','applied_in_ram_awaiting_native_save')
                and not (native_io.get('operation')=='read' and tick>journal.get('native_io_tick',0)))
            if valid:
                notices=folder/'notifications.json'
                rows[previous]=dict(state=journal['state_after'],notifications=json.loads(notices.read_text(encoding='utf8')) if notices.exists() else [])
    return rows


class Bridge:
    def __init__(self,*,apply=False):
        self.apply=apply
        process=portable.session_process()
        self.process=process
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
        self.mutex=kernel.CreateMutexW(None,True,f'Local\\Server16BankTest_{process.pid}')
        if not self.mutex or ctypes.get_last_error()==183:
            if self.mutex:kernel.CloseHandle(self.mutex)
            raise RuntimeError('Ja existe uma ponte de emprestimos para esta sessao')
        self.memory=Memory();m=self.memory
        m.process_id=process.pid
        m.process_handle=m.kernel32.OpenProcess(0x410,False,process.pid)
        if not m.process_handle:raise OSError('FIFA nao permite leitura')
        m.base_module=m._get_base_address(process.exe())
        self.offsets=json.loads(portable.OFFSETS.read_text(encoding='utf8'))
        self.save=read_active_save(GAME,m)
        self.session=f"{self.save['process_created_100ns']}:{process.pid}"
        profile=competition_session(m,True)
        if not isinstance(profile,dict) or profile.get('career_role')!=1:raise RuntimeError('Abra uma carreira de treinador')
        self.club=profile['club_id'];self.context_address=profile['context_address']
        self.userid=profile['userid']
        self.scope=fingerprint((self.save['path'].casefold()+'|'+str(self.club)).encode())[:20]
        self.snapshots=STATE/self.scope/'snapshots';self.snapshots.mkdir(parents=True,exist_ok=True)
        saved=self.saved()
        self.saved_hash=saved['hash']
        self.saved_wage_budget=saved['wage_budget'];self.currency=saved['currency']
        # A dismissal/job change updates this selected native context before
        # the next DATA write. The native save I/O still identifies the career;
        # the current club and its money must come from the verified RAM slot.
        live=self.live()
        if saved['userid']!=profile['userid'] or live['club']!=self.club:raise RuntimeError('Usuário da carreira diverge da RAM')
        if live['date']<saved['date']:raise RuntimeError('Aguardando a data da carreira terminar de carregar')
        self.live_wage_valid=(saved['club']!=self.club or m.read_uint32(self.context_address+0x2a8)==self.saved_wage_budget)
        self.club_states=career_clubs(self.save,saved,live,profile,self.session,self.io_record())
        initial=self.snapshots/(saved['hash']+'.json')
        portable_state=self.club_states.get(self.club)
        if portable_state:
            self.state=portable_state['state']
            write_json(STATE/self.scope/'notifications.json',portable_state['notifications'])
        elif initial.exists():self.state=json.loads(initial.read_text(encoding='utf8'))['state']
        elif saved['club']!=self.club:
            self.state=empty(self.club,live['date'])
        else:
            if list(self.snapshots.glob('*.json')):raise RuntimeError('Este save nao possui snapshot financeiro conhecido; teste suspenso')
            self.state=empty(self.club,saved['date'])
            write_json(initial,{'save_hash':saved['hash'],'date':saved['date'],'budget':saved['budget'],'state':self.state})
        if self.state['club']!=self.club:raise RuntimeError('Histórico financeiro pertence a outro clube')
        # Retain a verified unsaved debt across worker restarts. A prepared
        # journal is never reapplied; first inspect its exact RAM result.
        pending=STATE/self.scope/'pending.json'
        if pending.exists():
            journal=json.loads(pending.read_text(encoding='utf8'))
            recovered=recover_pending(self.state,live,journal,self.session,self.io_record(),saved['hash'])
            if recovered is not self.state and journal.get('reason')=='loan_confirmed':
                contract=recovered['contracts'][-1]
                loan_notifications.record(STATE/self.scope,loan_notifications.make_notice(contract['id'],journal['before'],
                    approved=True,bank=contract['bank'],amount=contract['principal'],budget_after=journal['after_budget'],
                    message='Sua contratação foi aprovada e o crédito foi aplicado.',contract=contract,deliver_date=journal['before']['date']))
            if recovered is not self.state and journal.get('reason')=='loan_refused' and recovered.get('last_decision'):
                decision=recovered['last_decision']
                loan_notifications.record(STATE/self.scope,loan_notifications.make_notice(decision['id'],journal['before'],
                    approved=False,bank=decision['bank'],amount=decision['principal'],budget_after=journal['after_budget'],
                    message=decision['message'],application=decision,deliver_date=decision['decided_date']))
            self.state=recovered
        if self.state['last_date']>live['date']:raise RuntimeError('Aguardando o estado financeiro da carreira carregada')
        self.last_save=(saved['hash'],self.save['operation'] if 'operation' in self.save else '')
        self.io_tick=int(self.io_record().get('access_tick_ms',0))
        self.last_sequence=0;self.last_scan=0.;self.write_handle=None;self.scan_regions=[];self.result=None
        self.last_write_tick=None
        self.last_advance=(None,None)
        self.nonce=f'B57_{process.pid}_{self.club}_{secrets.token_hex(6)}';self.view_signature=None;self.ui_signature=None;self.feedback=''
        from finance_inputs import FinanceInputs
        self.finance_reader=FinanceInputs(GAME);self.finance_next=0.;self.finance_ack=0
        self.finance_signature=None;self.finance_error=None;self.finance_context=None;self.finance_result=None
        if self.apply:
            self.write_handle=m.kernel32.OpenProcess(0x438,False,process.pid)
            if not self.write_handle:raise OSError('FIFA nao permite aplicar o orcamento')
        log('attached',pid=process.pid,session=self.session,club=self.club,save=self.save['path'],budget=live['budget'],date=live['date'],apply=self.apply,
            budget_address=hex(live['address']),writes='only explicit loan credit and scheduled installments; no DATA/INDEX edits')
        write_json(STATE/'status.json',{'pid':process.pid,'active':True,'apply':self.apply,'club':self.club,'save':self.save['path'],'budget':live['budget'],'date':live['date']})
        for index,default in enumerate(BANK_DEFAULTS):BANKS[index].update(default)
        self.bank_sidecar=self.save['path'];self.last_catalog_poll=0;self.refresh_catalog()
        loan_notifications.reconcile(STATE/self.scope,self.state)
        self.request_reader=None if self.direct_input_ready() else RequestReader(self.process,self.memory.base_module,self.nonce)
        self.flush_notifications(live)
        self.checkpoint_club()
        self.publish_view(live)

    def refresh_catalog(self):
        if not getattr(self,'bank_sidecar',None):return
        now=time.monotonic()
        if now-getattr(self,'last_catalog_poll',0)<1:return
        self.last_catalog_poll=now;changed=False
        for index,slug,name,bps in save_sidecar.bank_rows(self.bank_sidecar):
            if not 3<=index<len(BANKS) or slug!=BANK_DEFAULTS[index]['id'] or not 1<=len(name)<=60 or not 10<=bps<=1000:continue
            if (BANKS[index]['name'],BANKS[index]['rate_bps'])!=(name,bps):
                BANKS[index].update(name=name,rate_bps=bps);changed=True
        if hasattr(self,'finance_reader'):
            policy,banks=save_sidecar.credit_rules(self.bank_sidecar)
            if (getattr(self,'credit_policy',None),getattr(self,'credit_banks',None))!=(policy,banks):
                self.credit_policy,self.credit_banks=policy,banks;changed=True
        if changed:self.ui_signature=None;self.view_signature=None

    def persist_journal(self,journal):
        write_json(STATE/self.scope/'pending.json',journal)
        if getattr(self,'bank_sidecar',None):save_sidecar.write_journal(self.bank_sidecar,journal)

    def checkpoint_club(self):
        if not hasattr(self,'club_states'):return
        path=STATE/self.scope/'notifications.json'
        notices=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
        row=dict(state=self.state,notifications=notices)
        self.club_states[self.club]=row
        signature=fingerprint(json.dumps([self.saved_hash,row],sort_keys=True,ensure_ascii=False).encode())
        if signature==getattr(self,'club_checkpoint_signature',None):return
        save_sidecar.save_session_club(self.save['path'],self.saved_hash,self.session,self.io_tick,self.state,notices)
        self.club_checkpoint_signature=signature

    def persist_sidecar(self,saved,record):
        path=STATE/self.scope/'notifications.json'
        notices=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
        target=save_sidecar.save_snapshot(self.save['path'],saved,self.state,notices,record,clubs=getattr(self,'club_states',{}))
        self.bank_sidecar=self.save['path']
        log('native_save_sqlite',path=str(target),hash=saved['hash'],date=saved['date'])

    def ui_stable(self,live,screen):
        # Calendar simulation must not wait for the expensive APT compilers.
        # Compile on the visible destination, or after a stable menu pause.
        page=live.get('page','').casefold()
        if page==screen.casefold():return True
        if page in (PAGE.casefold(),FINANCE_PAGE.casefold()):return False
        key=(live['club'],live['date'],live['budget'],live.get('context_epoch'))
        now=time.monotonic()
        if key!=getattr(self,'ui_context',None):
            self.ui_context=key;self.ui_context_since=now
        return now-getattr(self,'ui_context_since',now)>=1

    def publish_view(self,live):
        wage=self.memory.read_uint32(self.context_address+0x2a8) if self.live_wage_valid else self.saved_wage_budget
        view=presentation(self.state,live['date'],live['budget'],nonce=self.nonce,pid=self.process.pid,error=self.feedback,ready=self.apply,wage_budget=wage,currency=self.currency,wage_source='save/RAM cross-check' if self.live_wage_valid else 'last native save')
        from club_identity import club_name
        view['club_name']=club_name(GAME,self.club,self.save['path'])
        view['result']=self.result
        if hasattr(self,'finance_reader'):
            credit=self.credit_view(live)
            view['credit']=credit
            if not credit or not any(b['amounts'] and not b['retry_date'] for b in credit['banks'].values()):
                view.update(can_borrow=False,credit_error='Sem crédito disponível; confira a dívida e as carências dos bancos.' if credit else 'Aguardando divisão e prestígio confirmados do clube.')
        if self.state.get('finance') and not self.state['finance']['settings']['enabled']:
            view.update(can_borrow=False,error='Movimentações financeiras desativadas. Reative em Finanças do clube → Configurações.')
        if not self.apply:view.update(can_borrow=False,error='Ponte em modo de leitura; nenhuma movimentação disponível.')
        signature=fingerprint(json.dumps(view,sort_keys=True,ensure_ascii=False).encode())
        if signature!=self.view_signature:
            write_json(STATE/'finance_view.json',view);self.view_signature=signature
        if signature!=self.ui_signature and self.ui_stable(live,PAGE):self.publish_screen(view,signature)

    def publish_screen(self,view,signature):
        # A presentation/compiler failure must never stop the financial clock,
        # lose the recovered ledger, or suppress observing a completed save.
        now=time.monotonic()
        if now<getattr(self,'ui_retry_after',0):return False
        try:
            import bank_ui_r57
            bank_ui_r57.build(view)
            source=HERE/'package/data/ui/game/screens/career/server16/bankloans.big'
            target=GAME/'data/ui/game/screens/career/server16/bankloansv2.big'
            temp=target.with_suffix('.new');temp.write_bytes(source.read_bytes());temp.replace(target)
        except Exception as error:
            message=str(error);self.ui_retry_after=now+3
            if message!=getattr(self,'ui_error',None):log('financial_ui_retry',error=message)
            self.ui_error=message
            return False
        if getattr(self,'ui_error',None):log('financial_ui_recovered')
        self.ui_error=None;self.ui_retry_after=0;self.ui_signature=signature
        return True

    def page(self):
        return self.memory.get_string(self.offsets['ORIPGBASE'],self.offsets['PG1'],128)

    def live(self):
        m=self.memory;p=competition_session(m,True)
        if not isinstance(p,dict) or p.get('career_role')!=1 or p['club_id']!=self.club or p['context_address']!=self.context_address:
            raise RuntimeError('Contexto da carreira mudou; ponte suspensa')
        ctx=p['context_address'];reg=p['registry_address']
        # Verify the descriptor used by the installed native calendar module.
        code=m.read_process_memory(m.base_module+0x44563f0,24)
        if code[7:9]!=b'\xc7\x01':raise RuntimeError('Descritor de calendario divergente')
        idx=struct.unpack_from('<I',code,9)[0]
        if not 0<=idx<256:raise RuntimeError('Calendario fora do registro')
        calendar=m.read_int64(m.read_int64(reg+idx*32+24))
        day,month,year=struct.unpack('<3i',m.read_process_memory(calendar+0x34,12))
        today=year*10000+month*100+day;parse_date(today)
        budget=m.read_uint32(ctx+0x2ac)
        if not 0<=budget<=MAX_BUDGET:raise RuntimeError('Orcamento fora da faixa')
        return {'club':p['club_id'],'date':today,'budget':budget,'address':ctx+0x2ac,'page':self.page(),'context_epoch':p.get('context_epoch',0),'currency':getattr(self,'currency',None)}

    def saved(self):
        path=Path(self.save['path']);data=path.read_bytes()
        career=CareerRead(data,GAME/'data/db/fifa_ng_db-meta.xml');context=career.context()
        dates={r.GetIntField('currdate') for r in career.rows('career_calendar')}
        if len(dates)!=1:raise RuntimeError('Data do save ambigua')
        pref=career.one('career_managerpref','managerprefid',context['userid'])
        return {'hash':fingerprint(data),'date':next(iter(dates)),'budget':context['budget'],'userid':context['userid'],'club':context['club_id'],'wage_budget':pref.GetIntField('wagebudget'),'currency':context['currency']}

    def io_record(self):
        records=[]
        for filename in ('career_active_save.tsv','career_save_source.tsv'):
            path=GAME/'ModCarrerMode/runtime'/filename
            try:
                row=dict(line.split('=',1) for line in path.read_text(encoding='utf-8-sig').splitlines() if '=' in line)
                if (int(row.get('schema',0))==3 and int(row.get('pid',0))==self.process.pid
                        and int(row.get('process_created_100ns',0))==self.save['process_created_100ns']
                        and row.get('complete_file')=='1' and row.get('path','').casefold()==self.save['path'].casefold()):
                    records.append(row)
            except (ValueError,OSError):continue
        return max(records,key=lambda r:int(r.get('access_tick_ms',0)),default={})

    def scan(self):
        if self.direct_input_ready():
            if getattr(self,'request_reader',None):
                self.request_reader.close();self.request_reader=None
            live=self.live()
            rows=read_direct_request(STATE,pid=self.process.pid,club=self.club,context=self.context_address,
                epoch=live['context_epoch'],nonce=self.nonce)
            self.request_transport='native_event'
            try:self.request_capture_ns=(STATE/'native_request.tsv').stat().st_mtime_ns
            except OSError:self.request_capture_ns=None
            return rows
        self.request_transport='legacy_heap'
        if getattr(self,'request_reader',None):return self.request_reader.read()
        return self.scan_bounded()

    def direct_input_ready(self):
        try:
            row=dict(line.split('=',1) for line in (STATE/'native_input_ready.tsv').read_text(encoding='ascii').splitlines() if '=' in line)
            return row.get('schema')=='1' and row.get('pid')==str(self.process.pid) and row.get('ready')=='1'
        except (OSError,UnicodeError):return False

    def scan_bounded(self):
        m=self.memory;k=m.kernel32;now=time.monotonic()
        if now-getattr(self,'inventory_time',0)>15 or not getattr(self,'scan_inventory',None):
            previous=getattr(self,'scan_inventory',[])
            cursor=getattr(self,'scan_cursor',0)
            previous_base=previous[cursor][0] if previous and cursor<len(previous) else None
            previous_offset=getattr(self,'scan_offset',0)
            query=k.VirtualQueryEx;query.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.POINTER(Region),ctypes.c_size_t];query.restype=ctypes.c_size_t
            address=0x10000;regions=[]
            while address<0x7fffffffffff:
                info=Region()
                if not query(m.process_handle,address,ctypes.byref(info),ctypes.sizeof(info)):break
                base=info.base or address;end=base+info.size
                if end<=address:break
                address=end
                if info.state==0x1000 and info.type==0x20000 and not info.protect&0x101 and info.protect&0xcc:regions.append((base,info.size))
            self.scan_inventory=sorted(regions,key=lambda row:row[1]);self.inventory_time=now;self.scan_cursor=0;self.scan_offset=0
            for index,(base,size) in enumerate(self.scan_inventory):
                if base==previous_base and previous_offset<size:
                    self.scan_cursor=index;self.scan_offset=previous_offset;break
        found=set();began=time.monotonic();budget=64*1024**2
        for base,size in getattr(self,'priority_chunks',[]):
            try:found.update(requests_in(m.read_process_memory(base,size),self.nonce))
            except RuntimeError:pass
        if not hasattr(self,'priority_chunks'):self.priority_chunks=[]
        if any(row[0]>self.last_sequence for row in found):return sorted(found)
        for base,size in getattr(self,'request_arenas',[]):
            try:found.update(requests_in(m.read_process_memory(base,size),self.nonce))
            except RuntimeError:pass
        if any(row[0]>self.last_sequence for row in found):return sorted(found)
        while self.scan_inventory and budget>0 and time.monotonic()-began<.08:
            base,size=self.scan_inventory[self.scan_cursor];count=min(2*1024**2,size-self.scan_offset);start=base+self.scan_offset;length=min(count+1024,size-self.scan_offset)
            try:got=requests_in(m.read_process_memory(start,length),self.nonce)
            except RuntimeError:got=set()
            found.update(got)
            if got and (start,length) not in self.priority_chunks:
                self.priority_chunks=(self.priority_chunks+[(start,length)])[-6:]
                arena_start=max(base,start-2*1024**2);arena_end=min(base+size,start+4*1024**2)
                arena=(arena_start,arena_end-arena_start)
                self.request_arenas=(getattr(self,'request_arenas',[])+[arena])[-2:]
            self.scan_offset+=count;budget-=count
            if self.scan_offset>=size:self.scan_offset=0;self.scan_cursor=(self.scan_cursor+1)%len(self.scan_inventory)
            if any(row[0]>self.last_sequence for row in got):break
        return sorted(found)

    def legacy_scan(self):
        m=self.memory;k=m.kernel32
        query=k.VirtualQueryEx;query.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.POINTER(Region),ctypes.c_size_t];query.restype=ctypes.c_size_t
        address=0x10000;found=set();read_bytes=0;start=time.monotonic();regions=[]
        while address<0x7fffffffffff:
            info=Region()
            if not query(m.process_handle,address,ctypes.byref(info),ctypes.sizeof(info)):break
            base=info.base or address;end=base+info.size
            if end<=address:break
            address=end
            if info.state!=0x1000 or info.type!=0x20000 or info.protect&0x101 or not info.protect&0x0c:continue
            tail=b''
            for offset in range(0,info.size,4*1024**2):
                if time.monotonic()-start>8 or read_bytes>3*1024**3:break
                try:blob=m.read_process_memory(base+offset,min(4*1024**2,info.size-offset))
                except RuntimeError:tail=b'';continue
                got=requests_in(tail+blob,self.nonce);found.update(got);read_bytes+=len(blob);tail=blob[-256:]
                if got:regions.append([hex(base+offset),len(blob)])
            if found or time.monotonic()-start>8 or read_bytes>3*1024**3:break
        log('screen_request_scan',bytes=read_bytes,seconds=round(time.monotonic()-start,3),requests=sorted(found),regions=regions)
        return sorted(found)

    def publish(self,before,new_state,new_budget,events,reason,result=None):
        if new_budget-before['budget']!=club_finance.cash_delta(events):
            raise ValueError('Lançamentos não conciliam com a alteração do orçamento; nenhuma escrita realizada')
        if new_budget==before['budget']:
            if reason in ('loan_requested','loan_refused','finance_settings','club_finance','crowd_observation'):
                if not self.apply:return
                self.persist_journal(dict(session=self.session,reason=reason,before=before,
                    after_budget=new_budget,state_before=self.state,state_after=new_state,events=events,
                    status='request_registered',native_io_tick=self.io_tick,source_save_hash=self.saved_hash))
                for event in events:log('request_registered',reason=reason,transaction=event)
            self.state=new_state;self.result=result or self.result
            if reason=='loan_requested':loan_notifications.record(STATE/self.scope,loan_notifications.request_notice(new_state['application']))
            if result:self.feedback=result.get('message','')
            self.flush_notifications(before)
            self.checkpoint_club();return
        if not self.apply:
            log('dry_run',reason=reason,before=before['budget'],after=new_budget,events=events);return
        # Pause until the native UI and financial fields are stable. No executable
        # bytes are changed and no foreign function/thread is run in FIFA.
        time.sleep(.2)
        actual=self.live()
        if actual!=before:raise RuntimeError('O jogo mudou durante a preparacao; nenhuma escrita realizada')
        allowed=financial_page(actual['page'])
        if not allowed:raise RuntimeError('Tela insegura para aplicar o orcamento')
        journal={'session':self.session,'reason':reason,'before':before,'after_budget':new_budget,'state_before':self.state,'state_after':new_state,'events':events,'status':'prepared','native_io_tick':self.io_tick}
        self.persist_journal(journal)
        payload=struct.pack('<I',new_budget);buffer=ctypes.create_string_buffer(payload);written=ctypes.c_size_t()
        k=self.memory.kernel32
        ok=k.WriteProcessMemory(self.write_handle,ctypes.c_void_p(before['address']),buffer,4,ctypes.byref(written))
        if not ok or written.value!=4:raise OSError('Nao foi possivel publicar o orcamento')
        if self.memory.read_uint32(before['address'])!=new_budget:raise RuntimeError('A verificacao do orcamento falhou; ponte encerrada')
        self.last_cash_change=dict(date=before['date'],before=before['budget'],after=new_budget,delta=new_budget-before['budget'],verified=True)
        self.state=new_state;journal['status']='applied_in_ram_awaiting_native_save'
        self.persist_journal(journal)
        for event in events:log('transaction',reason=reason,budget_before=before['budget'],budget_after=new_budget,transaction=event)
        loan_notifications.payment_notice(STATE/self.scope,new_state,before,new_budget,events)
        write_json(STATE/'status.json',{'pid':self.process.pid,'active':True,'last_action':reason,'budget':new_budget,'date':before['date'],'events':events,'awaiting_native_save':True})
        self.feedback='Pagamento aplicado. Salve a carreira no FIFA.' if reason!='loan_confirmed' else 'Crédito aplicado. Salve a carreira no FIFA.'
        if reason=='club_finance':self.feedback='Finanças do clube atualizadas. Salve a carreira no FIFA.'
        if result:self.result=dict(result,ok=True,budget=new_budget,message=self.feedback,contract_id=next((e['id'] for e in events if e.get('id')),result.get('contract_id')))
        if reason=='loan_confirmed':
            contract=new_state['contracts'][-1]
            loan_notifications.record(STATE/self.scope,loan_notifications.make_notice(contract['id'],before,
                approved=True,bank=contract['bank'],amount=contract['principal'],budget_after=new_budget,
                message='Sua contratação foi aprovada e o crédito foi aplicado.',contract=contract,deliver_date=contract.get('decision_date',before['date'])))
            self.feedback+=' O e-mail de aprovação está na fila da caixa de mensagens.'
            if result:self.result['message']=self.feedback
        self.flush_notifications(dict(before,budget=new_budget))
        self.checkpoint_club()

    def flush_notifications(self,live):
        # Publish the native outbox before expensive APT/texture generation.
        loan_notifications.reconcile(STATE/self.scope,self.state)
        loan_notifications.schedule_reminders(STATE/self.scope,self.state)
        loan_notifications.dispatch(STATE/self.scope,STATE,live,pid=self.process.pid,context=self.context_address,state=self.state)

    def observe_save(self):
        try:current=read_active_save(GAME,self.memory)
        except (OSError,ValueError):
            # Save As can remove the source slot before publishing its complete
            # replacement. Retain the ledger and suspend transactions meanwhile.
            self.live()
            return False
        if current['path'].casefold()!=self.save['path'].casefold():
            # FIFA may Save As/autosave to a new slot. Transfer this ledger only
            # after a completed native WRITE in the same verified RAM context.
            previous=self.save;self.save=current
            try:record=self.io_record();saved=self.saved();live=self.live()
            except (OSError,ValueError):
                self.save=previous
                return False
            matches=(saved['club']==self.club and saved['date']==live['date'] and saved['budget']==live['budget'])
            if record.get('operation')=='read' and matches:
                self.save=previous
                raise RuntimeError('Outro slot foi carregado; aguardando seu próprio estado financeiro')
            if record.get('operation')!='write' or not matches:
                self.save=previous
                return False
            old_scope=self.scope
            self.saved_hash=saved['hash']
            self.scope=fingerprint((current['path'].casefold()+'|'+str(self.club)).encode())[:20]
            self.snapshots=STATE/self.scope/'snapshots';self.snapshots.mkdir(parents=True,exist_ok=True)
            notices=STATE/old_scope/'notifications.json'
            if notices.exists():write_json(STATE/self.scope/'notifications.json',json.loads(notices.read_text(encoding='utf8')))
            write_json(self.snapshots/(saved['hash']+'.json'),dict(saved,state=self.state))
            self.persist_sidecar(saved,record)
            self.io_tick=int(record.get('access_tick_ms',0));log('native_save_slot_followed',club=self.club,budget=saved['budget']);return
        record=self.io_record();tick=int(record.get('access_tick_ms',0))
        version_changed=(current['size'],current['mtime_ns'])!=(self.save['size'],self.save['mtime_ns'])
        if not version_changed and tick==self.io_tick:return
        previous=self.save;self.save=current
        try:saved=self.saved();live=self.live()
        except (OSError,ValueError):
            self.save=previous
            return False
        if saved['budget']!=live['budget'] or saved['date']!=live['date'] or saved['club']!=self.club:
            self.save=previous
            return False
        self.io_tick=tick;snapshot=self.snapshots/(saved['hash']+'.json')
        self.saved_hash=saved['hash']
        if record.get('operation')=='read':
            self.club_states=save_sidecar.load_clubs(self.save['path'],saved['hash'])
            portable_state=self.club_states.get(self.club)
            if portable_state:
                self.state=portable_state['state'];write_json(snapshot,dict(saved,state=self.state));write_json(STATE/self.scope/'notifications.json',portable_state['notifications'])
            if not snapshot.exists():raise RuntimeError('Save desconhecido carregado; teste suspenso sem inferir parcelas')
            self.state=json.loads(snapshot.read_text(encoding='utf8'))['state'];log('known_save_snapshot',hash=saved['hash'],date=saved['date']);return
        if record.get('operation')!='write':raise RuntimeError('Mudanca de save sem registro nativo de leitura/gravacao')
        self.persist_sidecar(saved,record)
        if snapshot.exists():
            recorded=json.loads(snapshot.read_text(encoding='utf8'))['state']
            if recorded==self.state:return
        write_json(snapshot,dict(saved,state=self.state))
        pending=STATE/self.scope/'pending.json'
        if pending.exists():
            journal=json.loads(pending.read_text(encoding='utf8'));journal['status']='native_saved';self.persist_journal(journal)
        log('native_save_snapshot',hash=saved['hash'],date=saved['date'],budget=saved['budget'],path=current['path'])

    def tick(self):
        if (STATE/'STOP').exists():raise RuntimeError('Teste interrompido pelo arquivo STOP')
        if self.observe_save() is False:return
        self.refresh_catalog();live=self.live();now=time.monotonic()
        self.observe_attendance(live)
        if live['page'].casefold()==PAGE.casefold():self.last_bank_seen=now
        # The reader remains active on Central, Calendar and every other page.
        # Leaving Loans must never suspend receipt of an already submitted click.
        if now-self.last_scan>.08:
            self.last_scan=now
            requests=self.scan()
            if requests:
                live=self.live()
                found=max(requests);seq,action,bank,ai,ti=found[:5]
                submitted=found[5] if len(found)>5 else live['date']
                if seq>self.last_sequence:
                    self.last_sequence=seq
                    captured=getattr(self,'request_capture_ns',None)
                    log('screen_request_received',sequence=seq,submitted_date=submitted,observed_date=live['date'],page=live['page'],
                        transport=getattr(self,'request_transport','legacy_heap'),capture_delay_ms=round(max(0,time.time_ns()-captured)/1e6,1) if captured else None)
                    try:
                        request_id=self.nonce+':'+str(seq)
                        if live['page'].casefold()==FINANCE_PAGE.casefold():
                            if action!=2 or not 0<=bank<len(club_finance.SWITCHES) or ai not in (0,1) or ti!=0 or 'finance' not in self.state:
                                raise ValueError('Configuração financeira inválida ou ainda não carregada')
                            state=club_finance.toggle(self.state,club_finance.SWITCHES[bank],bool(ai),live['date'])
                            self.publish(live,state,live['budget'],[],'finance_settings')
                            self.finance_ack=seq;self.finance_signature=None;self.finance_next=0.;self.last_advance=(None,None)
                            self.finance_result=dict(sequence=seq,ok=True,message='Configuração aplicada.')
                            if hasattr(self,'finance_reader'):self.publish_club_finance(live)
                            return
                        if not self.finance_enabled():raise ValueError('Movimentações financeiras desativadas nas configurações do clube')
                        if action==0:
                            credit=self.credit_view(live,refresh=True) if hasattr(self,'finance_reader') else None
                            if hasattr(self,'finance_reader') and not credit:raise ValueError('Aguardando dados atuais de divisão e prestígio do clube')
                            state,budget,events=request_loan(self.state,request_id=request_id,club=live['club'],today=live['date'],budget=live['budget'],bank=bank,amount=AMOUNTS[ai],months=TERMS[ti],submitted_on=submitted,currency=getattr(self,'currency',None),credit=credit)
                        else:state,budget,events=pay(self.state,request_id=request_id,club=live['club'],today=live['date'],budget=live['budget'],settle=action==2,contract_id=found[6] if len(found)>6 else None)
                        result={'sequence':seq,'action':action}
                        if action and len(found)>6:result['contract_id']=found[6]
                        if action==0:result.update(ok=True,kind='loan_requested',submitted_date=state['application']['date'],decision_date=state['application']['decision_date'],message='Solicitação registrada. A data de resposta permanece vinculada ao envio.')
                        self.publish(live,state,budget,events,'loan_requested' if action==0 else 'loan_settled' if action==2 else 'installment_advanced',result)
                    except ValueError as e:
                        self.feedback=str(e);self.result={'sequence':seq,'action':action,'ok':False,'budget':live['budget'],'message':str(e)};log('request_refused',sequence=seq,error=str(e))
                        if live['page'].casefold()==FINANCE_PAGE.casefold():
                            self.finance_ack=seq;self.finance_result=dict(sequence=seq,ok=False,message=str(e));self.finance_signature=None
                            if hasattr(self,'finance_reader'):self.publish_club_finance(live)
        live=self.live()
        if financial_page(live['page']):
            self.run_club_finance(live)
            live=self.live()
            key=(live['date'],live['budget'])
            if self.finance_enabled('loans') and key!=self.last_advance:
                self.last_advance=key
                state,budget,events=advance(self.state,club=live['club'],today=live['date'],budget=live['budget'])
                self.publish(live,state,budget,events,'monthly_installment')
            live=self.live()
            credit=self.credit_view(live) if hasattr(self,'finance_reader') else None
            can_decide=self.finance_enabled() and (not hasattr(self,'finance_reader') or credit is not None)
            state,budget,events,decision=decide_loan(self.state,club=live['club'],today=live['date'],budget=live['budget'],credit=credit) if can_decide else (self.state,live['budget'],[],None)
            if decision:
                self.feedback=decision['message']
                result=None
                if self.result and self.result.get('kind')=='loan_requested':
                    result=dict(self.result,kind='loan_decision',ok=decision['approved'],message=decision['message'])
                self.publish(live,state,budget,events,'loan_confirmed' if decision['approved'] else 'loan_refused',result)
                if not decision['approved']:
                    loan_notifications.record(STATE/self.scope,loan_notifications.make_notice(decision['id'],live,
                        approved=False,bank=decision['bank'],amount=decision['principal'],budget_after=live['budget'],
                        message=decision['message'],application=decision,deliver_date=decision['decision_date']))
        self.flush_notifications(self.live())
        self.checkpoint_club();self.publish_view(self.live())

    def observe_attendance(self,live):
        if not hasattr(self,'finance_reader') or not self.state.get('finance'):return
        now=time.monotonic()
        if now<getattr(self,'crowd_next',0):return
        self.crowd_next=now+.5
        from match_attendance import observe
        reading=observe(GAME,self.save['path'],live,pid=self.process.pid,created=self.save.get('process_created_100ns'))
        context=getattr(self,'finance_context',None) or {}
        if reading and context.get('club')==live['club'] and context.get('capacity'):reading['capacity']=context['capacity']
        state,changed=club_finance.record_attendance(self.state,reading,live['date'])
        if changed:self.publish(live,state,live['budget'],[],'crowd_observation')

    def credit_view(self,live,refresh=False):
        from credit_policy import offers
        context=getattr(self,'finance_context',None)
        if refresh or not context or context.get('club')!=live['club'] or context.get('date')!=live['date']:
            try:
                context=self.finance_reader.read(self.save['path'],live,pid=self.process.pid,userid=self.userid,
                    created=self.save.get('process_created_100ns'))
                self.finance_context=context
            except (OSError,ValueError,KeyError,ImportError):return None
        if not hasattr(self,'credit_policy'):
            self.credit_policy,self.credit_banks=save_sidecar.credit_rules(self.save['path'])
        return offers(self.state,context.get('club_profile'),live['date'],self.credit_policy,self.credit_banks)

    def finance_enabled(self,kind=None):
        settings=self.state.get('finance',{}).get('settings',{})
        return settings.get('enabled',True) and (kind is None or settings.get(kind,True))

    def run_club_finance(self,live):
        # Existing unit/legacy bridge instances lack the new optional reader.
        if not hasattr(self,'finance_reader') or time.monotonic()<self.finance_next:return
        self.finance_next=time.monotonic()+1
        try:
            context=self.finance_reader.read(self.save['path'],live,pid=self.process.pid,userid=self.userid,
                created=self.save.get('process_created_100ns'))
            policy=save_sidecar.finance_rules(self.save['path'])
            state,budget,events=club_finance.apply(self.state,club=self.club,today=live['date'],budget=live['budget'],context=context,policy=policy)
        except (OSError,ValueError,KeyError,ImportError) as error:
            if str(error)!=self.finance_error:log('club_finance_waiting',error=str(error))
            self.finance_error=str(error)
            self.publish_club_finance(live)
            return
        self.finance_error=None;self.finance_context=context
        # Publication failures retain the existing guarded bridge semantics:
        # never catch an ambiguous write and then blindly replay it next tick.
        if state!=self.state or budget!=live['budget']:self.publish(live,state,budget,events,'club_finance')
        self.publish_club_finance(self.live())

    def publish_club_finance(self,live):
        book=self.state.get('finance',{});context=self.finance_context or {}
        current=book.get('season');wage=context.get('coach_wage')
        view=dict(last_cash_change=getattr(self,'last_cash_change',None),ready=bool(book) and not self.finance_error,club=self.club,club_name=context.get('club_name','Clube'),
            date=live['date'],budget=live['budget'],currency=self.currency,start=book.get('start'),
            settings=book.get('settings',dict.fromkeys(club_finance.SWITCHES,True)),nonce=self.nonce,
            ack=self.finance_ack,setting_result=getattr(self,'finance_result',None),months=club_finance.monthly(self.state),cash_months=club_finance.monthly(self.state,settlement=True),coach_monthly=round(wage*52/12) if wage is not None else None,
            agreements=[r for r in book.get('agreements',{}).values() if r['season']==current])
        view.update(budget_initial=context.get('budget_initial'),player_weekly=context.get('player_weekly'),
            wage_margin=self.memory.read_uint32(self.context_address+0x2a8) if self.live_wage_valid else self.saved_wage_budget)
        from finance_people import debts
        view.update(players=context.get('players',[]),transfers=context.get('transfers',[]),
            player_error=context.get('player_error'),transfer_error=context.get('transfer_error'),
            debts=debts(self.state['contracts'],BANKS),
            entries=book.get('entries',[]),coach_weekly=wage,commercial=book.get('commercial',{}),
            fixtures=context.get('fixtures',[]),rules=book.get('rules',dict(club_finance.DEFAULT_RULES)))
        if self.finance_error:view['message']=self.finance_error
        signature=fingerprint(json.dumps(view,ensure_ascii=False,sort_keys=True).encode())
        try:
            if signature!=self.finance_signature:
                if not self.ui_stable(live,FINANCE_PAGE):
                    write_json(STATE/'club_finance_view.json',view);return
                import finance_ui
                target=GAME/'data/ui/game/screens/career/server16/clubfinance.big';temporary=target.with_suffix('.new')
                # The finance view is generated while the career is live. A
                # save switch or manager change during the build must not
                # publish a screen carrying the previous club/context into the
                # next navigation frame.
                self.validate_finance_publication_context(live)
                temporary.unlink(missing_ok=True)
                finance_ui.build(view,temporary)
                self.validate_finance_publication_context(live)
                temporary.replace(target)
                write_json(STATE/'club_finance_view.json',view);self.finance_signature=signature
            # Calendar ignores custom SendSystemEvent navigation. Use the same
            # scoped UI-owner readiness queue as the market/preview screens.
            # Refresh the timestamp even when the package did not change.
            self.publish_finance_ready(live,signature)
        except Exception as error:
            # UI failure must not stop loans, payments or observing native saves.
            log('club_finance_ui_retry',error=str(error))

    def validate_finance_publication_context(self,live):
        profile=competition_session(self.memory,True)
        if (not isinstance(profile,dict) or profile.get('club_id')!=self.club
            or profile.get('context_address')!=self.context_address
            or profile.get('context_epoch')!=live['context_epoch'] or self.live()!=live):
            raise ValueError('Contexto mudou antes de publicar o painel financeiro')
        return profile

    def publish_finance_ready(self,live,revision):
        import prepared_views
        profile=self.validate_finance_publication_context(live)
        prepared_views.publish(STATE/'view_ready.tsv',dict(pid=self.process.pid,
            process_created_100ns=self.save['process_created_100ns']),profile,live['date'],revision)

    def close(self):
        if getattr(self,'request_reader',None):self.request_reader.close()
        if getattr(self,'write_handle',None):self.memory.kernel32.CloseHandle(self.write_handle)
        if getattr(self,'mutex',None):ctypes.WinDLL('kernel32').CloseHandle(wintypes.HANDLE(self.mutex))
        if getattr(self,'memory',None):self.memory.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--inspect',action='store_true');args=parser.parse_args()
    bridge=None
    try:
        bridge=Bridge(apply=args.apply)
        if args.inspect:
            print(json.dumps(bridge.live(),ensure_ascii=False));return
        while bridge.process.is_running():bridge.tick();time.sleep(.5)
    except Exception as error:
        log('stopped',error=str(error));print(str(error));write_json(STATE/'status.json',{'active':False,'error':str(error)})
    finally:
        if bridge:
            bridge.close()
            log('detached',pid=bridge.process.pid,session=bridge.session)
            write_json(STATE/'status.json',{'active':False,'pid':bridge.process.pid,'session':bridge.session,'apply':bridge.apply})

if __name__=='__main__':main()
