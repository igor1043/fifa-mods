"""Scoped outbox for real FIFA inbox messages; never grants credit itself."""
from datetime import timedelta
import hashlib,json,os
from pathlib import Path
from loans import BANKS,parse_date,write_json


def money(value):return f'{value:,}'.replace(',','.')


def make_notice(request_id,live,*,approved,bank,amount,budget_after,message,contract=None,application=None,deliver_date=None):
    due=deliver_date if deliver_date is not None else int((parse_date(live['date'])+timedelta(days=1)).strftime('%Y%m%d'))
    body=[(contract or {}).get('bank_name',BANKS[bank]['name']),message,'',
          'Valor solicitado: '+money(amount),
          'Orçamento antes: '+money(live['budget']),
          'Orçamento após a operação: '+money(budget_after)]
    if contract:
        body += ['','Solicitação enviada: '+parse_date(contract.get('application_date',contract['date'])).strftime('%d/%m/%Y'),
                 'Resposta prevista: '+parse_date(contract.get('decision_date',contract['date'])).strftime('%d/%m/%Y'),
                 'Análise concluída: '+parse_date(contract['date']).strftime('%d/%m/%Y'),
                 'Primeira parcela: '+parse_date(contract['payments'][0]['date']).strftime('%d/%m/%Y'),
                 'Parcela mensal: '+money(contract['payment']),
                 'Prazo: '+str(contract['months'])+' meses']
    elif application:
        body += ['', 'Solicitação enviada: '+parse_date(application['date']).strftime('%d/%m/%Y'),
                 'Resposta prevista: '+parse_date(application['decision_date']).strftime('%d/%m/%Y'),
                 'Análise concluída: '+parse_date(application['decided_date']).strftime('%d/%m/%Y')]
    if approved:body+=['','O crédito foi conferido no orçamento de transferências.']
    else:body+=['','Nenhum crédito foi aplicado ao orçamento.']
    return dict(id=hashlib.sha256(request_id.encode()).hexdigest(),request_id=request_id,
                club=live['club'],due=due,approved=approved,delivered=False,
                kind='decision',subject='Empréstimo aprovado' if approved else 'Empréstimo não aprovado',body='\n'.join(body))


def record(folder,notice):
    path=Path(folder)/'notifications.json'
    rows=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
    existing=next((row for row in rows if row['id']==notice['id']),None)
    if existing is None:rows.append(notice)
    else:
        # Refresh only our content (including legacy garbled literals), keeping
        # the native acknowledgement and its session identity untouched.
        updated=dict(existing,**{k:v for k,v in notice.items() if k not in ('delivered','delivery_key','delivered_date')})
        if updated==existing:return
        existing.clear();existing.update(updated)
    write_json(path,rows)


def dispatch(folder,runtime,live,*,pid,context,state):
    path=Path(folder)/'notifications.json'
    if state['club']!=live['club'] or not path.exists():
        (Path(runtime)/'native_mail_request.tsv').unlink(missing_ok=True);return
    rows=json.loads(path.read_text(encoding='utf8'));changed=False;queued=False
    receipt={}
    try:receipt=dict(line.split('=',1) for line in (Path(runtime)/'native_mail_receipt.tsv').read_text().splitlines() if '=' in line)
    except OSError:pass
    contracts={c['id']:c for c in state['contracts'] if c.get('club',state['club'])==live['club']}
    valid=set(contracts)
    priorities={'application':0,'decision':1,'payment':2,'reminder':3}
    for row in sorted(rows,key=lambda row:(row['due'],priorities.get(row.get('kind'),1))):
        if row['club']!=live['club']:continue
        if row.get('kind')=='application' and not any(a['id']==row['request_id'] for a in state.get('applications',[])):continue
        if row['approved'] and row['request_id'] not in valid:continue
        delivery_key=f"{pid}:{context:x}:{live['context_epoch']}"
        if row['delivered'] and row.get('delivery_key')==delivery_key:continue
        if (receipt.get('id')==row['id'] and receipt.get('pid')==str(pid) and receipt.get('club')==str(live['club'])
                and receipt.get('epoch')==str(live['context_epoch']) and receipt.get('context')==f'{context:x}'):
            row['delivered']=True;row['delivery_key']=delivery_key;row['delivered_date']=int(receipt['date']);changed=True;continue
        if row.get('kind')=='reminder':
            # Consume an actual native receipt even if the calendar/payment
            # advanced before Python observed it. Never send a late reminder.
            contract=contracts.get(row['request_id'])
            if not contract or contract['paid']>=row['number'] or live['date']>=row['payment_date']:continue
        if live['date']<row['due']:continue
        payload=f"schema=1\npid={pid}\nclub={row['club']}\ncontext={context:x}\nepoch={live['context_epoch']}\ndue={row['due']}\nid={row['id']}\nsubject={row['subject'].encode('utf8').hex()}\nbody={row['body'].encode('utf8').hex()}\n"
        target=Path(runtime)/'native_mail_request.tsv'
        if not target.exists() or target.read_text()!=payload:
            temporary=target.with_suffix('.new');temporary.write_text(payload,encoding='ascii');os.replace(temporary,target)
        queued=True;break
    if not queued:(Path(runtime)/'native_mail_request.tsv').unlink(missing_ok=True)
    if changed:write_json(path,rows)


def schedule_reminders(folder,state):
    """Queue D-1 reminders once; skip missed reminders after the actual due day."""
    path=Path(folder)/'notifications.json'
    rows=json.loads(path.read_text(encoding='utf8')) if path.exists() else []
    ids={r['id'] for r in rows};changed=False
    for contract in state['contracts']:
        if contract.get('club',state['club'])!=state['club']:continue
        for payment in contract['payments'][contract['paid']:]:
            token=contract['id']+':reminder:'+str(payment['number'])
            ident=hashlib.sha256(token.encode()).hexdigest()
            if ident in ids:continue
            due=int((parse_date(payment['date'])-timedelta(days=1)).strftime('%Y%m%d'))
            rows.append(dict(id=ident,request_id=contract['id'],club=state['club'],due=due,approved=True,
                delivered=False,kind='reminder',number=payment['number'],payment_date=payment['date'],
                subject='Empréstimo: parcela vence amanhã',
                body='\n'.join((contract.get('bank_name',BANKS[contract['bank']]['name']),'',
                    'A parcela '+str(payment['number'])+'/'+str(contract['months'])+' vence em '+parse_date(payment['date']).strftime('%d/%m/%Y')+'.',
                    'Valor: '+money(payment['amount']),
                    'A cobrança será descontada do orçamento de transferências.',
                    'Mantenha saldo disponível ou antecipe o pagamento em Empréstimos.'))))
            ids.add(ident);changed=True
    if changed:write_json(path,rows)


def payment_notice(folder,state,before,after,events):
    payments=[e for e in events if e.get('event') in ('installment','manual_installment')]
    if not payments:return
    ids={e['id'] for e in payments}
    for ident in ids:
        contract=next(c for c in state['contracts'] if c['id']==ident)
        entries=[e for e in payments if e['id']==ident]
        due_dates=sorted({e['date'] for e in entries})
        dates=' a '.join(parse_date(d).strftime('%d/%m/%Y') for d in (due_dates[:1] if len(due_dates)==1 else (due_dates[0],due_dates[-1])))
        token=ident+':paid:'+','.join(str(e['number']) for e in entries)+':'+str(before['date'])
        record(folder,dict(id=hashlib.sha256(token.encode()).hexdigest(),request_id=ident,
            club=state['club'],due=before['date'],approved=True,delivered=False,kind='payment',
            subject='Empréstimo quitado' if contract['paid']==contract['months'] else 'Empréstimo: pagamento confirmado',
            body='\n'.join((contract.get('bank_name',BANKS[contract['bank']]['name']),'',
                'Pagamento aplicado em: '+parse_date(before['date']).strftime('%d/%m/%Y'),
                'Vencimentos cobrados: '+dates,
                'Parcelas pagas: '+', '.join(str(e['number']) for e in entries),
                'Valor descontado: '+money(sum(e['amount'] for e in entries)),
                'Orçamento antes: '+money(before['budget']),
                'Orçamento após a operação: '+money(after),
                'Falta pagar: '+money(sum(p['amount'] for p in contract['payments'][contract['paid']:]))))))


def request_notice(application):
    """A separate immediate receipt, with dates from the immutable application."""
    a=application;offer=a.get('quote',{});bank=offer.get('bank_name',BANKS[a['bank']]['name'])
    return dict(id=hashlib.sha256((a['id']+':submitted').encode()).hexdigest(),request_id=a['id'],
        club=a['club'],due=a['date'],approved=False,delivered=False,kind='application',
        subject='Empréstimo: pedido recebido',
        body='\n'.join((bank,'Recebemos a solicitação de empréstimo do clube.','',
            'Pedido enviado em: '+parse_date(a['date']).strftime('%d/%m/%Y'),
            'Resposta prevista: '+parse_date(a['decision_date']).strftime('%d/%m/%Y'),
            'Valor solicitado: '+money(a['principal']),
            'Prazo: '+str(a['months'])+' meses',
            'A aprovação ou recusa será enviada nesta caixa de mensagens.',
            'O envio do pedido não altera o orçamento do clube.')))


def reconcile(folder,state):
    """Recover missing notices from recorded decisions without replaying money."""
    for a in state.get('applications',[]):
        record(folder,request_notice(a))
        if a.get('status') not in ('approved','refused'):continue
        contract=next((c for c in state['contracts'] if c['id']==a['id']),None)
        approved=a['status']=='approved'
        if approved and contract is None:continue
        before=dict(club=state['club'],date=a['decided_date'],budget=a['budget_before'])
        record(folder,make_notice(a['id'],before,approved=approved,bank=a['bank'],amount=a['principal'],
            budget_after=a['budget_after'],message=a.get('message','Análise concluída.'),
            contract=contract,application=a,deliver_date=a['decision_date']))
