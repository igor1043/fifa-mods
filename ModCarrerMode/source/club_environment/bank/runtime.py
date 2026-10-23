import portable_paths as portable
"""Experimental bank bridge: native-screen requests, guarded budget, save snapshots.

Never edits DATA, INDEX, executable code, assets in RAM, camera, or input state.
Only an explicit request from the separate bank screen enables a 4-byte budget
publication. Scheduled debits require this same career and an idle hub page.
"""
from pathlib import Path
import argparse,ctypes,json,re,struct,sys,time,os,secrets
from ctypes import wintypes
import psutil
from server16_py.memory_access import Memory
from server16_py.career_context import competition_session
from server16_py.career_active_save import read_active_save
from server16_py.career_read import CareerRead
from loans import *
from build_screen import PAGE,NONCE

GAME=portable.GAME
HERE=Path(__file__).resolve().parent
LOG=HERE/'runtime/bank_loans.log'
STATE=HERE/'runtime'
PATTERN=re.compile(r'S16BANK_V1\|'+NONCE+r'\|([0-9]{1,6})\|([0-2])\|([0-3])\|([0-2])\|END_S16BANK')


class Region(ctypes.Structure):
    _fields_=[('base',ctypes.c_void_p),('allocation',ctypes.c_void_p),('allocation_protect',wintypes.DWORD),
              ('partition',wintypes.WORD),('size',ctypes.c_size_t),('state',wintypes.DWORD),
              ('protect',wintypes.DWORD),('type',wintypes.DWORD)]


def log(event,**fields):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('a',encoding='utf8') as stream:
        stream.write(json.dumps(dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**fields),ensure_ascii=False)+'\n')


def requests_in(data,nonce=NONCE):
    pattern=re.compile(r'S16BANK_V2\|'+re.escape(nonce)+r'\|([0-9]{1,9})\|([0-2])\|([0-2])\|([0-3])\|([0-2])\|END_S16BANK')
    found=set()
    for encoding in ('ascii','utf-16-le'):
        needle=('S16BANK_V2|'+nonce+'|').encode(encoding)
        start=data.find(needle)
        while start>=0:
            text=data[start:start+256].decode(encoding,errors='ignore')
            match=pattern.match(text)
            if match:found.add(tuple(map(int,match.groups())))
            start=data.find(needle,start+len(needle))
    return found


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
        self.offsets=json.loads(portable.OFFSETS.read_text())
        self.save=read_active_save(GAME,m)
        self.session=f"{self.save['process_created_100ns']}:{process.pid}"
        profile=competition_session(m,True)
        if not isinstance(profile,dict) or profile.get('career_role')!=1:raise RuntimeError('Abra uma carreira de treinador')
        self.club=profile['club_id'];self.context_address=profile['context_address']
        self.scope=fingerprint((self.save['path'].casefold()+'|'+str(self.club)).encode())[:20]
        self.snapshots=STATE/self.scope/'snapshots';self.snapshots.mkdir(parents=True,exist_ok=True)
        saved=self.saved()
        self.saved_wage_budget=saved['wage_budget'];self.currency=saved['currency']
        # Cross-check this readonly native field against the current saved
        # manager preference before presenting it as a live wage budget.
        self.live_wage_valid=m.read_uint32(self.context_address+0x2a8)==self.saved_wage_budget
        live=self.live()
        if saved['club']!=self.club or live['club']!=self.club:raise RuntimeError('Clube do save diverge da RAM')
        if saved['budget']!=live['budget'] or saved['date']!=live['date']:
            raise RuntimeError('Salve a carreira antes de iniciar o teste: data/orcamento da RAM ainda difere do save')
        initial=self.snapshots/(saved['hash']+'.json')
        if initial.exists():self.state=json.loads(initial.read_text())['state']
        else:
            if list(self.snapshots.glob('*.json')):raise RuntimeError('Este save nao possui snapshot financeiro conhecido; teste suspenso')
            self.state=empty(self.club,live['date'])
            write_json(initial,{'save_hash':saved['hash'],'date':saved['date'],'budget':saved['budget'],'state':self.state})
        self.last_save=(saved['hash'],self.save['operation'] if 'operation' in self.save else '')
        self.io_tick=int(self.io_record().get('access_tick_ms',0))
        self.last_sequence=0;self.last_scan=0.;self.write_handle=None;self.scan_regions=[];self.result=None
        self.last_write_tick=None
        self.last_advance=(None,None)
        self.nonce=f'B57_{process.pid}_{self.club}_{secrets.token_hex(6)}';self.view_signature=None;self.ui_signature=None;self.feedback=''
        if self.apply:
            self.write_handle=m.kernel32.OpenProcess(0x438,False,process.pid)
            if not self.write_handle:raise OSError('FIFA nao permite aplicar o orcamento')
        log('attached',pid=process.pid,session=self.session,club=self.club,save=self.save['path'],budget=live['budget'],date=live['date'],apply=self.apply,
            budget_address=hex(live['address']),writes='only explicit loan credit and scheduled installments; no DATA/INDEX edits')
        write_json(STATE/'status.json',{'pid':process.pid,'active':True,'apply':self.apply,'club':self.club,'save':self.save['path'],'budget':live['budget'],'date':live['date']})
        self.publish_view(live)

    def publish_view(self,live):
        wage=self.memory.read_uint32(self.context_address+0x2a8) if self.live_wage_valid else self.saved_wage_budget
        view=presentation(self.state,live['date'],live['budget'],nonce=self.nonce,pid=self.process.pid,error=self.feedback,ready=self.apply,wage_budget=wage,currency=self.currency,wage_source='save/RAM cross-check' if self.live_wage_valid else 'last native save')
        view['result']=self.result
        if not self.apply:view.update(can_borrow=False,error='Ponte em modo de leitura; nenhuma movimentação disponível.')
        signature=fingerprint(json.dumps(view,sort_keys=True,ensure_ascii=False).encode())
        if signature!=self.view_signature:
            write_json(STATE/'finance_view.json',view);self.view_signature=signature
        if signature!=self.ui_signature:
            import bank_ui_r57
            bank_ui_r57.build(view)
            source=HERE/'package/data/ui/game/screens/career/server16/bankloans.big';target=GAME/'data/ui/game/screens/career/server16/bankloansv2.big';temp=target.with_suffix('.new');temp.write_bytes(source.read_bytes());temp.replace(target);self.ui_signature=signature

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
        return {'club':p['club_id'],'date':today,'budget':budget,'address':ctx+0x2ac,'page':self.page()}

    def saved(self):
        path=Path(self.save['path']);data=path.read_bytes()
        career=CareerRead(data,GAME/'data/db/fifa_ng_db-meta.xml');context=career.context()
        dates={r.GetIntField('currdate') for r in career.rows('career_calendar')}
        if len(dates)!=1:raise RuntimeError('Data do save ambigua')
        pref=career.one('career_managerpref','managerprefid',context['userid'])
        return {'hash':fingerprint(data),'date':next(iter(dates)),'budget':context['budget'],'club':context['club_id'],'wage_budget':pref.GetIntField('wagebudget'),'currency':context['currency']}

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
        return self.scan_bounded()

    def scan_bounded(self):
        m=self.memory;k=m.kernel32;now=time.monotonic()
        if now-getattr(self,'inventory_time',0)>15 or not getattr(self,'scan_inventory',None):
            query=k.VirtualQueryEx;query.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.POINTER(Region),ctypes.c_size_t];query.restype=ctypes.c_size_t
            address=0x10000;regions=[]
            while address<0x7fffffffffff:
                info=Region()
                if not query(m.process_handle,address,ctypes.byref(info),ctypes.sizeof(info)):break
                base=info.base or address;end=base+info.size
                if end<=address:break
                address=end
                if info.state==0x1000 and info.type==0x20000 and not info.protect&0x101 and info.protect&0x0c and info.size<=256*1024**2:regions.append((base,info.size))
            self.scan_inventory=regions;self.inventory_time=now;self.scan_cursor=0;self.scan_offset=0
        found=set();began=time.monotonic();budget=32*1024**2
        for base,size in getattr(self,'priority_chunks',[]):
            try:found.update(requests_in(m.read_process_memory(base,size),self.nonce))
            except RuntimeError:pass
        if not hasattr(self,'priority_chunks'):self.priority_chunks=[]
        while self.scan_inventory and budget>0 and time.monotonic()-began<.04:
            base,size=self.scan_inventory[self.scan_cursor];count=min(512*1024,size-self.scan_offset);start=base+self.scan_offset;length=min(count+256,size-self.scan_offset)
            try:got=requests_in(m.read_process_memory(start,length),self.nonce)
            except RuntimeError:got=set()
            found.update(got)
            if got and (start,length) not in self.priority_chunks:self.priority_chunks=(self.priority_chunks+[(start,length)])[-6:]
            self.scan_offset+=count;budget-=count
            if self.scan_offset>=size:self.scan_offset=0;self.scan_cursor=(self.scan_cursor+1)%len(self.scan_inventory)
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
        if new_budget==before['budget']:
            self.state=new_state;self.result=result or self.result;self.publish_view(before);return
        if not self.apply:
            log('dry_run',reason=reason,before=before['budget'],after=new_budget,events=events);return
        # Pause until the native UI and financial fields are stable. No executable
        # bytes are changed and no foreign function/thread is run in FIFA.
        time.sleep(.2)
        actual=self.live()
        if actual!=before:raise RuntimeError('O jogo mudou durante a preparacao; nenhuma escrita realizada')
        allowed=actual['page'].casefold() in (PAGE.casefold(),'game/screens/fluxhub/fluxhub','game/screens/misc/stadiumpan')
        if not allowed:raise RuntimeError('Tela insegura para aplicar o orcamento')
        journal={'session':self.session,'reason':reason,'before':before,'after_budget':new_budget,'state_before':self.state,'state_after':new_state,'events':events,'status':'prepared'}
        write_json(STATE/self.scope/'pending.json',journal)
        payload=struct.pack('<I',new_budget);buffer=ctypes.create_string_buffer(payload);written=ctypes.c_size_t()
        k=self.memory.kernel32
        ok=k.WriteProcessMemory(self.write_handle,ctypes.c_void_p(before['address']),buffer,4,ctypes.byref(written))
        if not ok or written.value!=4:raise OSError('Nao foi possivel publicar o orcamento')
        if self.memory.read_uint32(before['address'])!=new_budget:raise RuntimeError('A verificacao do orcamento falhou; ponte encerrada')
        self.state=new_state;journal['status']='applied_in_ram_awaiting_native_save'
        write_json(STATE/self.scope/'pending.json',journal)
        for event in events:log('transaction',reason=reason,budget_before=before['budget'],budget_after=new_budget,transaction=event)
        write_json(STATE/'status.json',{'pid':self.process.pid,'active':True,'last_action':reason,'budget':new_budget,'date':before['date'],'events':events,'awaiting_native_save':True})
        self.feedback='Pagamento aplicado. Salve a carreira no FIFA.' if reason!='loan_confirmed' else 'Crédito aplicado. Salve a carreira no FIFA.'
        if result:self.result=dict(result,ok=True,budget=new_budget,message=self.feedback)
        self.publish_view(dict(before,budget=new_budget))

    def observe_save(self):
        current=read_active_save(GAME,self.memory)
        if current['path'].casefold()!=self.save['path'].casefold():raise RuntimeError('Outro slot foi aberto; o teste nao transfere dividas entre saves')
        record=self.io_record();tick=int(record.get('access_tick_ms',0))
        version_changed=(current['size'],current['mtime_ns'])!=(self.save['size'],self.save['mtime_ns'])
        if not version_changed and tick==self.io_tick:return
        self.io_tick=tick
        self.save=current;saved=self.saved();live=self.live();snapshot=self.snapshots/(saved['hash']+'.json')
        if saved['budget']!=live['budget'] or saved['date']!=live['date'] or saved['club']!=self.club:
            raise RuntimeError('O save gravado diverge da RAM; revisar a persistencia antes de prosseguir')
        if record.get('operation')=='read':
            if not snapshot.exists():raise RuntimeError('Save desconhecido carregado; teste suspenso sem inferir parcelas')
            self.state=json.loads(snapshot.read_text())['state'];log('known_save_snapshot',hash=saved['hash'],date=saved['date']);return
        if record.get('operation')!='write':raise RuntimeError('Mudanca de save sem registro nativo de leitura/gravacao')
        if snapshot.exists():
            recorded=json.loads(snapshot.read_text())['state']
            if recorded!=self.state:raise RuntimeError('Save identico com estado financeiro diferente; investigar serializacao antes de prosseguir')
            return
        write_json(snapshot,dict(saved,state=self.state))
        log('native_save_snapshot',hash=saved['hash'],date=saved['date'],budget=saved['budget'],path=current['path'])

    def tick(self):
        if (STATE/'STOP').exists():raise RuntimeError('Teste interrompido pelo arquivo STOP')
        self.observe_save();live=self.live();now=time.monotonic()
        self.publish_view(live)
        if live['page'].casefold()==PAGE.casefold() and now-self.last_scan>.15:
            self.last_scan=now
            requests=self.scan()
            if requests:
                seq,action,bank,ai,ti=max(requests)
                if seq>self.last_sequence:
                    self.last_sequence=seq
                    try:
                        request_id=self.nonce+':'+str(seq)
                        if action==0:state,budget,events=borrow(self.state,request_id=request_id,club=live['club'],today=live['date'],budget=live['budget'],bank=bank,amount=AMOUNTS[ai],months=TERMS[ti])
                        else:state,budget,events=pay(self.state,request_id=request_id,club=live['club'],today=live['date'],budget=live['budget'],settle=action==2)
                        self.publish(live,state,budget,events,'loan_confirmed' if action==0 else 'loan_settled' if action==2 else 'installment_advanced',{'sequence':seq,'action':action})
                    except ValueError as e:
                        self.feedback=str(e);self.result={'sequence':seq,'action':action,'ok':False,'budget':live['budget'],'message':str(e)};self.publish_view(live);log('request_refused',sequence=seq,error=str(e))
        if live['page'].casefold() in ('game/screens/fluxhub/fluxhub','game/screens/misc/stadiumpan'):
            key=(live['date'],live['budget'])
            if key!=self.last_advance:
                self.last_advance=key
                state,budget,events=advance(self.state,club=live['club'],today=live['date'],budget=live['budget'])
                self.publish(live,state,budget,events,'monthly_installment')

    def close(self):
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
