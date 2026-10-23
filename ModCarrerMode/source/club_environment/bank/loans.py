"""Local test ledger. Game currency units are integers; no real bank services."""
from __future__ import annotations
from calendar import monthrange
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path

BANKS = (
    {"id": "aurora", "name": "Banco Aurora", "rate_bps": 80},
    {"id": "horizonte", "name": "Banco Horizonte", "rate_bps": 100},
    {"id": "uniao", "name": "Banco Uniao", "rate_bps": 120},
)
AMOUNTS = (1_000_000, 3_000_000, 5_000_000, 10_000_000)
TERMS = (6, 12, 24)
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


def quote(bank, amount, months):
    if type(bank) is not int or not 0 <= bank < len(BANKS):
        raise ValueError("Banco invalido")
    if amount not in AMOUNTS or months not in TERMS:
        raise ValueError("Valor ou prazo fora do prototipo")
    rate = Decimal(BANKS[bank]["rate_bps"]) / 10000
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
    return {"bank": bank, "principal": amount, "months": months,
            "rate_bps": BANKS[bank]["rate_bps"], "payment": payment,
            "total": sum(p["amount"] for p in payments), "payments": payments}


def empty(club, today):
    parse_date(today)
    return {"schema": 1, "club": club, "last_date": today, "contracts": [], "processed": []}


def borrow(state, *, request_id, club, today, budget, bank, amount, months):
    """Return a proposed new state and budget; caller owns guarded publication."""
    if request_id in state["processed"]:
        return deepcopy(state), budget, []
    if club != state["club"] or today < state["last_date"]:
        raise ValueError("A carreira mudou; carregue o estado associado ao save")
    parse_date(today)
    if not 0 <= budget <= MAX_BUDGET - amount:
        raise ValueError("O credito excede o limite de orcamento")
    if any(c["paid"] < c["months"] for c in state["contracts"]):
        raise ValueError("Quite o contrato atual antes de contratar outro")
    if sum(c['date']//10000==today//10000 for c in state['contracts'])>=2:
        raise ValueError('Limite de dois empréstimos no ano da carreira atingido')
    contract = quote(bank, amount, months)
    contract.update(id=request_id, club=club, date=today, paid=0)
    for payment in contract["payments"]:
        payment["date"] = next_month(today, payment["number"])
    result = deepcopy(state)
    result["contracts"].append(contract)
    result["processed"].append(request_id)
    result["last_date"] = today
    return result, budget + amount, [{"event": "credit", "id": request_id, "amount": amount,
                                    "date": today, "bank": BANKS[bank]["name"]}]


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


def pay(state, *, request_id, club, today, budget, settle=False):
    if request_id in state['processed']:return deepcopy(state),budget,[]
    parse_date(today)
    if club!=state['club'] or today<state['last_date']:raise ValueError('A carreira mudou')
    if not 0<=budget<=MAX_BUDGET:raise ValueError('Orçamento inválido')
    result=deepcopy(state);contract=next((c for c in result['contracts'] if c['paid']<c['months']),None)
    if contract is None:raise ValueError('Não há empréstimo em aberto')
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
    active=next((c for c in state['contracts'] if c['paid']<c['months']),None)
    used=sum(c['date']//10000==today//10000 for c in state['contracts'])
    history=active or (state['contracts'][-1] if state['contracts'] else None)
    schedule=[]
    if history:
        for p in history['payments']:
            status='Paga' if p['number']<=history['paid'] else ('Vencida' if p['date']<=today else 'A vencer')
            schedule.append(dict(p,status=status))
    return dict(club=state['club'],date=today,budget=budget,active=active,used=used,can_borrow=active is None and used<2,schedule=schedule,**extra)


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
