"""Confirmed native prize receipts. This module has no money-writing path."""
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib,json,struct,time

SUBJECT='CM_Email_PrizeMoney_Subject'
BODY='CM_Email_PrizeMoney'
VARIANTS=(0x3031850,0x3031880,0x3070e28)


def valid_day(value):
    if type(value) is not int:return False
    try:date(value//10000,value//100%100,value%100);return 19000101<=value<=22001231
    except ValueError:return False


def receipt(club,day,amount,competition,ordinal=0):
    if (type(club) is not int or not 0<club<2_000_000 or not valid_day(day)
        or type(amount) is not int or not 0<amount<=2_147_483_647
        or type(competition) is not int or not 0<competition<2_000_000
        or type(ordinal) is not int or not 0<=ordinal<4096):raise ValueError('Premiação nativa inválida')
    identity=hashlib.sha256(json.dumps([club,day,amount,competition,ordinal],separators=(',',':')).encode()).hexdigest()
    return dict(id=identity,club=club,date=day,amount=amount,competition=competition,
        ordinal=ordinal,source='FIFA · aviso de premiação',status='credited')


class NativePrizes:
    """Bounded read of the active career inbox; never scans heaps or calls FIFA."""
    def __init__(self,memory):
        self.memory=memory;self.identity=None;self.next=0.;self.last=None

    def read(self,*,pid,club,today,epoch=None,context_address=None):
        key=(pid,club,today,epoch,context_address)
        if key==self.identity and time.monotonic()<self.next:return self.last
        self.identity=key;self.next=time.monotonic()+.5
        if self.memory is None:
            self.last=dict(available=False,entries=[]);return self.last
        try:
            self.last=self._read(pid,club,today,epoch,context_address)
        except Exception as error:
            self.last=dict(available=False,entries=[],error=str(error))
        return self.last

    def _read(self,pid,club,today,epoch,context_address):
        from server16_py.career_context import competition_session
        m=self.memory
        if m.process_id!=pid:raise ValueError('A sessão do FIFA mudou')
        session=competition_session(m,True)
        if (not isinstance(session,dict) or session.get('club_id')!=club or session.get('career_role')!=1
            or epoch is not None and session.get('context_epoch')!=epoch
            or context_address is not None and session.get('context_address')!=context_address):raise ValueError('A carreira mudou durante a consulta de premiações')
        read=m.read_process_memory;base=m.base_module
        def pointer(address):return struct.unpack('<Q',read(address,8))[0]
        code=read(base+0x44565f0,24)
        if code[7:9]!=b'\xc7\x01':raise ValueError('Descritor da caixa de mensagens incompatível')
        index=struct.unpack_from('<I',code,9)[0]
        if index>255:raise ValueError('Registro da caixa de mensagens inválido')
        manager=pointer(pointer(session['registry_address']+index*32+24))
        if pointer(manager+8)!=session['registry_address'] or struct.unpack('<I',read(manager+0x168,4))[0]:raise ValueError('A caixa de mensagens está sendo atualizada')
        seen=set();found=[];headers=[]
        for slot in range(2):
            vector=read(manager+0x50+slot*0x40,16);headers.append(vector);start,end=struct.unpack('<QQ',vector)
            if end<start or end-start>4096*8 or (end-start)%8:raise ValueError('Lista de mensagens incompatível')
            pointers=struct.unpack('<'+'Q'*((end-start)//8),read(start,end-start)) if end>start else ()
            for raw in pointers:
                if raw in seen:continue
                seen.add(raw);header=read(raw,0xa8)
                if struct.unpack_from('<I',header,8)[0]!=club:continue
                subject,body=struct.unpack_from('<Q',header,0x48)[0],struct.unpack_from('<Q',header,0x58)[0]
                if not subject or not body:continue
                if read(subject,len(SUBJECT)+1)!=SUBJECT.encode()+b'\0':continue
                if read(body,len(BODY)+1)!=BODY.encode()+b'\0':continue
                if struct.unpack_from('<I',header,0x70)[0]!=3:raise ValueError('Argumentos da premiação incompatíveis')
                day=struct.unpack_from('<I',header,0x90)[0]
                if not valid_day(day) or day>today:continue
                head=raw+0x60;at=struct.unpack_from('<Q',header,0x68)[0];previous=head;values=[]
                for expected in VARIANTS:
                    if at==head:raise ValueError('Premiação incompleta')
                    prev,nxt,value=struct.unpack('<QQQ',read(at,24))
                    if prev!=previous:raise ValueError('A mensagem mudou durante a leitura')
                    variant=read(value,12)
                    if struct.unpack_from('<Q',variant)[0]!=base+expected:raise ValueError('Tipo dos valores da premiação incompatível')
                    values.append(struct.unpack_from('<I',variant,8)[0]);previous,at=at,nxt
                if at!=head or values[0]!=club or read(raw,0xa8)!=header:raise ValueError('A mensagem mudou durante a leitura')
                if values[1]:found.append((day,values[1],values[2]))
        if any(read(manager+0x50+slot*0x40,16)!=vector for slot,vector in enumerate(headers)) or competition_session(m,True)!=session:raise ValueError('A carreira mudou durante a leitura dos avisos')
        # An item can be present in both inbox vectors. Different native items
        # with identical contents retain their multiplicity, independently of RAM addresses.
        counts=Counter(found);entries=[]
        for (day,amount,competition),count in sorted(counts.items()):
            entries.extend(receipt(club,day,amount,competition,ordinal) for ordinal in range(count))
        return dict(available=True,entries=entries)


def entries(native,club=None,year=None,month=None):
    result={}
    for row in (native or {}).get('entries',[]):
        try:
            proof=receipt(row['club'],row['date'],row['amount'],row['competition'],row.get('ordinal',0))
            if row.get('id')!=proof['id'] or row.get('status')!='credited':continue
            if club is not None and row['club']!=club or year is not None and row['date']//10000!=year or month is not None and row['date']//100!=month:continue
            result[row['id']]=row
        except (ValueError,KeyError,TypeError):continue
    return sorted(result.values(),key=lambda r:(r['date'],r['id']),reverse=True)


def merge(previous,current,*,club,year):
    result=deepcopy(previous or {})
    for key,value in (current or {}).items():
        if key not in ('entries','prizes') and (value is not None or key not in result):result[key]=deepcopy(value)
    known={r['id']:deepcopy(r) for r in entries(previous,club,year)}
    for row in entries(current,club,year):known.setdefault(row['id'],deepcopy(row))
    if known:
        result['entries']=sorted(known.values(),key=lambda r:(r['date'],r['id']),reverse=True)
        result['prizes']=sum(r['amount'] for r in result['entries']);result['partial_history']=True
    else:result.setdefault('prizes',(current or {}).get('prizes'))
    return result


def project(book,current,*,club,today):
    year=today//10000
    previous=book.get('years',{}).get(str(year),{}).get('native_finance',{})
    return merge(previous,current,club=club,year=year)
