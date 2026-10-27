"""Local test ledger. Game currency units are integers; no real bank services."""
from __future__ import annotations
from calendar import monthrange
from copy import deepcopy
from datetime import date,timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path

BANKS = (
    {"id": "aurora", "name": "Banco Aurora", "rate_bps": 80},
    {"id": "horizonte", "name": "Banco Horizonte", "rate_bps": 100},
    {"id": "uniao", "name": "Banco Uniao", "rate_bps": 120},
)
# Append-only IDs preserve existing contracts; rates are fictional game offers.
BANKS += (
    {"id":"bb","name":"Banco do Brasil","rate_bps":80},
    {"id":"bmg","name":"Banco Bmg","rate_bps":130},
    {"id":"crefisa","name":"Crefisa","rate_bps":180},
    {"id":"sicredi","name":"Sicredi","rate_bps":65},
    {"id":"banrisul","name":"Banrisul","rate_bps":95},
)
BANKS += ({"id":"master","name":"Banco Master","rate_bps":145},)
BANKS += (
    {"id":"bradesco","name":"Bradesco","rate_bps":110},
    {"id":"itau","name":"Itaú","rate_bps":105},
    {"id":"caixa","name":"Caixa","rate_bps":85},
    {"id":"santander","name":"Santander","rate_bps":115},
)
# Public BCB averages are a calibration reference, not a quote for a club.
# See BANK_TERMS.md for observation dates and simulated risk premiums.
PREVIOUS_RATES={'bb':80,'bmg':130,'crefisa':180,'sicredi':65,'banrisul':95,
    'master':145,'bradesco':110,'itau':105,'caixa':85,'santander':115}
REFERENCE_RATES={'bb':205,'bmg':245,'crefisa':290,'sicredi':175,'banrisul':150,
    'master':265,'bradesco':226,'itau':205,'caixa':184,'santander':193}
RESPONSE_DAYS={'bb':3,'bmg':2,'crefisa':1,'sicredi':2,'banrisul':2,
    'master':4,'bradesco':1,'itau':2,'caixa':3,'santander':2}
# Fictional underwriting for gameplay only; not real bank approval statistics.
DECLINE_BPS={'bb':1200,'bmg':1000,'crefisa':800,'sicredi':1400,'banrisul':1000,
    'master':1800,'bradesco':1500,'itau':1600,'caixa':1400,'santander':1300}
for bank in BANKS:
    if bank['id'] in REFERENCE_RATES:bank['rate_bps']=REFERENCE_RATES[bank['id']]
BANK_DEFAULTS=tuple(dict(bank) for bank in BANKS)
OFFERED_BANKS=tuple(range(3,len(BANKS)))
# Append-only wire indexes keep pending V2/V3 requests compatible.
AMOUNTS = (1_000_000, 3_000_000, 5_000_000, 10_000_000, 20_000_000, 30_000_000, 50_000_000, 75_000_000, 100_000_000)
TERMS = (6, 12, 24, 36, 48)
MAX_ACTIVE = 2
MAX_PER_YEAR = 2
# Fictional game products, unrelated to real credit offers. Existing proposals
# and contracts retain their stored quote, independent of catalog changes.
PRODUCTS = {'bb':(50_000_000,48),'bmg':(20_000_000,36),'crefisa':(10_000_000,24),
    'sicredi':(20_000_000,36),'banrisul':(30_000_000,36),'master':(30_000_000,36),
    'bradesco':(75_000_000,48),'itau':(100_000_000,48),'caixa':(50_000_000,48),'santander':(100_000_000,48)}

def product_limits(bank):
    if type(bank) is not int or not 0<=bank<len(BANKS):raise ValueError('Banco inválido')
    return PRODUCTS.get(BANKS[bank]['id'],(10_000_000,24))

def amount_indices(bank):
    maximum,_=product_limits(bank)
    return tuple(i for i,value in enumerate(AMOUNTS) if value<=maximum)

def term_indices(bank):
    _,maximum=product_limits(bank)
    return tuple(i for i,value in enumerate(TERMS) if value<=maximum)

def offered(bank,amount,months):
    maximum,term=product_limits(bank)
    return amount in AMOUNTS and months in TERMS and amount<=maximum and months<=term

def quoted_rate(bank,amount,months):
    base=BANKS[bank]['rate_bps']
    if bank<3:return base # legacy prototype contracts/offers
    premium=next(extra for limit,extra in ((5_000_000,0),(10_000_000,25),(20_000_000,60),
        (30_000_000,110),(50_000_000,170),(75_000_000,240),(100_000_000,320)) if amount<=limit)
    return base+premium+(0 if months<=12 else 15 if months<=24 else 40 if months<=36 else 70)
MAX_BUDGET = 2_000_000_000


def parse_date(value):
    text = str(value)
    if len(text) != 8:
        raise ValueError("Data da carreira invalida")
    return date(int(text[:4]), int(text[4:6]), int(text[6:]))


def next_month(value, count):
    source = parse_date(value)
    month = source.year * 12 + source.month - 1 + count
    year, month0 = divmod(month, 12)
    month = month0 + 1
    day = min(source.day, monthrange(year, month)[1])
    return year * 10000 + month * 100 + day


def next_day(value):
    return int((parse_date(value)+timedelta(days=1)).strftime('%Y%m%d'))


def response_days(bank):
    if type(bank) is not int or not 0<=bank<len(BANKS):raise ValueError('Banco inválido')
    return RESPONSE_DAYS.get(BANKS[bank]['id'],1)


def response_date(value,bank):
    return int((parse_date(value)+timedelta(days=response_days(bank))).strftime('%Y%m%d'))


def quote(bank, amount, months):
    if type(bank) is not int or not 0 <= bank < len(BANKS):
        raise ValueError("Banco invalido")
    if not offered(bank,amount,months):
        raise ValueError('Valor ou prazo indisponível para este banco')
    rate_bps=quoted_rate(bank,amount,months)
    rate = Decimal(rate_bps) / 10000
    with localcontext() as context:
        context.prec = 40
        power = (1 + rate) ** months
        payment = int((amount * rate * power / (power - 1)).to_integral_value(rounding=ROUND_CEILING))
    balance = amount
    payments = []
    for index in range(months):
        interest = int((balance * rate).to_integral_value(rounding=ROUND_HALF_UP))
        due = balance + interest if index == months - 1 else min(payment, balance + interest)
        capital = due - interest
        balance -= capital
        payments.append({"number": index + 1, "amount": due, "interest": interest,
                         "principal": capital, "balance": balance})
    assert balance == 0 and sum(p["principal"] for p in payments) == amount
    return {"bank": bank, "bank_name": BANKS[bank]["name"], "principal": amount, "months": months,
            "rate_bps": rate_bps, "base_rate_bps":BANKS[bank]["rate_bps"], "payment": payment,
            "total": sum(p["amount"] for p in payments), "payments": payments}


def empty(club, today):
    parse_date(today)
    return {"schema": 1, "club": club, "last_date": today, "contracts": [], "processed": []}


def borrow(state, *, request_id, club, today, budget, bank, amount, months, offer=None):
    """Return a proposed new state and budget; caller owns guarded publication."""
    if request_id in state["processed"]:
        return deepcopy(state), budget, []
    if club != state["club"] or today < state["last_date"]:
        raise ValueError("A carreira mudou; carregue o estado associado ao save")
    parse_date(today)
    if state.get('application'):
        raise ValueError('Já existe uma solicitação em análise')
    if not 0 <= budget <= MAX_BUDGET - amount:
        raise ValueError("O credito excede o limite de orcamento")
    if sum(c["paid"]<c["months"] for c in state["contracts"])>=MAX_ACTIVE:
        raise ValueError('Limite de dois empréstimos ativos atingido')
    if sum(c['date']//10000==today//10000 for c in state['contracts'])>=MAX_PER_YEAR:
        raise ValueError('Limite de dois empréstimos no ano da carreira atingido')
    contract = deepcopy(offer) if offer is not None else quote(bank, amount, months)
    if (contract["bank"],contract["principal"],contract["months"])!=(bank,amount,months):raise ValueError("Proposta divergente")
    contract.setdefault("bank_name",BANKS[bank]["name"])
    contract.update(id=request_id, club=club, date=today, paid=0)
    for payment in contract["payments"]:
        payment["date"] = next_month(today, payment["number"])
    result = deepcopy(state)
    result["contracts"].append(contract)
    result["processed"].append(request_id)
    result["last_date"] = today
    return result, budget + amount, [{"event": "credit", "id": request_id, "amount": amount,
                                    "date": today, "bank": BANKS[bank]["name"]}]


def underwriting(state,request_id,budget,bank,amount,months,roll=None):
    """Freeze one draw per submitted proposal; reopening never rerolls it.

    Live request IDs contain the worker's random session nonce. Hashing that
    ID supplies a reproducible draw, including after SQLite/save restoration.
    """
    base=DECLINE_BPS.get(BANKS[bank]['id'],0)
    if not base:return None # Preserve legacy prototype applications.
    outstanding=sum(p['amount'] for c in state['contracts'] for p in c['payments'][c['paid']:])
    exposure=amount+outstanding
    ratio=exposure/max(1,budget)
    penalty=0 if ratio<=.25 else 400 if ratio<=.5 else 1000 if ratio<=1 else 2000 if ratio<=2 else 3500
    probability=min(6500,base+penalty+(300 if months>24 else 0))
    draw=int.from_bytes(hashlib.sha256(('loan-underwriting-v1|'+request_id).encode()).digest()[:8],'big')%10000 if roll is None else roll
    if type(draw) is not int or not 0<=draw<10000:raise ValueError('Sorteio de análise inválido')
    return dict(version=1,decline_bps=probability,roll=draw,budget_at_request=budget,outstanding_at_request=outstanding)

def request_loan(state, *, request_id, club, today, budget, bank, amount, months,submitted_on=None,currency=None,underwriting_roll=None):
    """Register an application; it changes neither budget nor contracted debt."""
    if 'request:'+request_id in state['processed']:
        return deepcopy(state),budget,[]
    submitted=today if submitted_on is None else submitted_on
    parse_date(submitted)
    if submitted>today:raise ValueError('A data da proposta está à frente da carreira')
    borrow(state,request_id=request_id,club=club,today=today,budget=budget,bank=bank,amount=amount,months=months)
    result=deepcopy(state)
    result['application']=dict(id=request_id,club=club,bank=bank,principal=amount,months=months,
                               date=submitted,decision_date=response_date(submitted,bank),response_days=response_days(bank),registered_date=today,budget_at_request=budget,status='pending',quote=quote(bank,amount,months))
    analysis=underwriting(state,request_id,budget,bank,amount,months,underwriting_roll)
    if analysis is not None:result['application']['underwriting']=analysis
    if currency in (0,1,2) and type(currency) is int:result['application']['currency']=currency
    result.setdefault('applications',[]).append(deepcopy(result['application']))
    result['processed'].append('request:'+request_id);result['last_date']=today
    return result,budget,[dict(event='application',id=request_id,date=submitted,decision_date=result['application']['decision_date'],registered_date=today)]


def decide_loan(state, *, club, today, budget):
    """Analyze due applications once, using the actual budget on decision day."""
    application=state.get('application')
    if not application or today<application['decision_date']:
        return deepcopy(state),budget,[],None
    if club!=state['club'] or today<state['last_date']:
        raise ValueError('A carreira mudou durante a análise')
    result=deepcopy(state);result.pop('application',None)
    response=dict(application,approved=False,decided_date=today,budget_before=budget,budget_after=budget)
    history=result.setdefault('applications',[])
    row=next((row for row in history if row['id']==application['id']),None)
    if row is None:row=deepcopy(application);history.append(row)
    try:
        analysis=application.get('underwriting')
        if analysis and analysis['roll']<analysis['decline_bps']:
            raise ValueError('O banco não aprovou esta proposta após a análise de risco. Nenhum valor foi creditado. Você pode solicitar a outro banco.')
        result,after,events=borrow(result,request_id=application['id'],club=club,today=today,budget=budget,
            bank=application['bank'],amount=application['principal'],months=application['months'],offer=application.get('quote'))
    except ValueError as error:
        result['processed'].append(application['id']);result['last_date']=today
        response['message']=str(error)
        row.update(status='refused',decided_date=today,budget_before=budget,budget_after=budget,message=str(error))
        result['last_decision']=deepcopy(row)
        return result,budget,[dict(event='application_refused',id=application['id'],date=today)],response
    response.update(approved=True,budget_after=after,message='Solicitação aprovada. O crédito foi aplicado ao orçamento.',contract=result['contracts'][-1])
    contract=result['contracts'][-1]
    contract.update(application_date=application['date'],decision_date=application['decision_date'])
    if 'currency' in application:contract['currency']=application['currency']
    row=next(row for row in result['applications'] if row['id']==application['id'])
    row.update(status='approved',decided_date=today,budget_before=budget,budget_after=after,message=response['message'])
    result['last_decision']=deepcopy(row)
    return result,after,events,response


def advance(state, *, club, today, budget):
    parse_date(today)
    if club != state["club"]:
        return deepcopy(state), budget, []
    if today < state["last_date"]:
        raise ValueError("Data retrocedeu; e necessario restaurar o snapshot deste save")
    if not 0 <= budget <= MAX_BUDGET:
        raise ValueError("Orcamento invalido")
    result = deepcopy(state)
    events = []
    for contract in result["contracts"]:
        for payment in contract["payments"][contract["paid"]:]:
            if payment["date"] > today:
                break
            if budget < payment["amount"]:
                # Preserve the unpaid principal and interest. No negative values,
                # write-off, or hidden second loan is created by the test.
                events.append({"event": "arrears", "id": contract["id"],
                               "number": payment["number"], "date": today,
                               "amount": payment["amount"]})
                break
            budget -= payment["amount"]
            contract["paid"] += 1
            payment.update(paid_date=today,method='automatic')
            events.append(dict(payment, event="installment", id=contract["id"]))
    result["last_date"] = today
    return result, budget, events


def pay(state, *, request_id, club, today, budget, settle=False, contract_id=None):
    if request_id in state['processed']:return deepcopy(state),budget,[]
    parse_date(today)
    if club!=state['club'] or today<state['last_date']:raise ValueError('A carreira mudou')
    if not 0<=budget<=MAX_BUDGET:raise ValueError('Orçamento inválido')
    result=deepcopy(state)
    active=[c for c in result['contracts'] if c['paid']<c['months']]
    if contract_id is None:
        if len(active)>1:raise ValueError('Selecione o contrato que deseja pagar')
        contract=next(iter(active),None)
    else:contract=next((c for c in active if c['id']==contract_id and c['club']==club),None)
    if contract is None:raise ValueError('Não há empréstimo em aberto para este contrato')
    pending=contract['payments'][contract['paid']:];selected=pending if settle else pending[:1]
    amount=sum(p['amount'] for p in selected)
    if budget<amount:raise ValueError('Saldo insuficiente para este pagamento')
    events=[]
    for payment in selected:
        payment.update(paid_date=today,method='manual');contract['paid']+=1
        events.append(dict(payment,event='manual_installment',id=contract['id']))
    result['processed'].append(request_id);result['last_date']=today
    return result,budget-amount,events


def presentation(state,today,budget,**extra):
    active_contracts=[c for c in state['contracts'] if c['paid']<c['months']]
    active=next(iter(active_contracts),None)
    used=sum(c['date']//10000==today//10000 for c in state['contracts'])
    history=active or (state['contracts'][-1] if state['contracts'] else None)
    schedule=[]
    if history:
        for p in history['payments']:
            status='Paga' if p['number']<=history['paid'] else ('Vencida' if p['date']<=today else 'A vencer')
            schedule.append(dict(p,status=status))
    application=state.get('application')
    contracts=[]
    for c in reversed(state['contracts']):
        rows=[dict(p,status='Paga' if p['number']<=c['paid'] else 'Vencida' if p['date']<=today else 'A vencer') for p in c['payments']]
        contracts.append(dict(c,schedule=rows,remaining=sum(p['amount'] for p in c['payments'][c['paid']:]),status='Ativo' if c['paid']<c['months'] else 'Quitado'))
    return dict(club=state['club'],date=today,budget=budget,active=active,application=application,last_decision=state.get('last_decision'),used=used,can_borrow=len(active_contracts)<MAX_ACTIVE and application is None and used<MAX_PER_YEAR,schedule=schedule,contracts=contracts,active_contracts=active_contracts,active_count=len(active_contracts),total_remaining=sum(p['amount'] for c in active_contracts for p in c['payments'][c['paid']:]),**extra)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    with pending.open("w", encoding="utf8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        import os
        os.fsync(stream.fileno())
    pending.replace(path)


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()
