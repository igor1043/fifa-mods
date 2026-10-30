"""Fictional club credit policy. All amounts stay in native career units.

Reference budget excludes borrowed cash. Division comes from current save
membership; no country, league or club allowlist is used.
"""
from copy import deepcopy

DEFAULTS = dict(tier_1_cap=150_000_000, tier_2_cap=12_000_000,
    tier_3_cap=4_000_000, tier_4_cap=1_500_000, tier_5_cap=750_000,
    budget_factor_bps=30_000, payroll_factor_bps=800,
    prestige_unit=45_000, minimum_capacity=250_000,
    recent_refusal_bps=900, arrears_bps=1800, max_decline_bps=9500)
# Different risk appetites, never exceeding the club's total credit facility.
BANK_FACTORS = dict(bb=8500, bmg=6500, crefisa=5500, sicredi=6000,
    banrisul=7500, master=9000, bradesco=9500, itau=10000,
    caixa=8000, santander=10000)

def rules(values=None):
    result=dict(DEFAULTS)
    for key,value in (values or {}).items():
        if key in result and type(value) is int and 0 < value <= 2_000_000_000:
            result[key]=value
    return result

def capacity(profile, policy=None):
    p=rules(policy)
    if not profile or not profile.get('club') or not profile.get('level') or not profile.get('overall'):
        return 0
    level=max(1,min(5,int(profile['level'])))
    prestige=max(0,min(20,int(profile.get('prestige') or 0)))
    overall=max(30,min(99,int(profile['overall'])))
    base=max(0,int(profile.get('base_budget') or 0))
    payroll=max(0,int(profile.get('player_weekly') or 0))*52
    structural=(base*p['budget_factor_bps']+payroll*p['payroll_factor_bps'])//10000
    structural+=prestige*prestige*p['prestige_unit']
    structural=structural*max(4000,min(13000,7000+(overall-50)*150))//10000
    return min(p[f'tier_{level}_cap'],max(p['minimum_capacity'],structural))

def principal_remaining(state):
    return sum(p['principal'] for c in state.get('contracts',[]) for p in c['payments'][c['paid']:])

def retry_date(state,bank,today):
    from loans import next_month
    dates=[next_month(a['decided_date'],1) for a in state.get('applications',[])
           if a.get('bank')==bank and a.get('status')=='refused' and a.get('decided_date',today+1)<=today]
    return max(dates,default=0)

def recent_refusals(state,today):
    from loans import next_month
    return sum(a.get('status')=='refused' and a.get('decided_date',today+1)<=today
               and today<next_month(a['decided_date'],1) for a in state.get('applications',[]))

def offers(state,profile,today,policy=None,bank_factors=None):
    from loans import BANKS,OFFERED_BANKS,product_limits,AMOUNTS
    total=capacity(profile,policy);debt=principal_remaining(state)
    factors=dict(BANK_FACTORS);factors.update(bank_factors or {})
    rows={}
    for bank in OFFERED_BANKS:
        slug=BANKS[bank]['id'];factor=max(1000,min(10000,int(factors.get(slug,7500))))
        limit=max(0,min(product_limits(bank)[0],total*factor//10000)-debt)
        retry=retry_date(state,bank,today)
        rows[str(bank)]=dict(limit=limit,retry_date=retry if retry>today else 0,
            amounts=sorted((i for i,v in enumerate(AMOUNTS) if v<=limit),key=lambda i:AMOUNTS[i]))
    return dict(profile=deepcopy(profile),capacity=total,principal_remaining=debt,banks=rows,
                policy=rules(policy),bank_factors=factors)

def validate(credit,bank,amount,today):
    from loans import parse_date
    if not credit or not credit.get('capacity'):
        raise ValueError('Aguardando divisão e prestígio confirmados do clube.')
    row=credit['banks'].get(str(bank))
    if row is None:raise ValueError('Banco indisponível para novas propostas.')
    if row['retry_date']>today:
        raise ValueError('Este banco recusou a última proposta. Tente novamente em '+parse_date(row['retry_date']).strftime('%d/%m/%Y')+'. Outros bancos podem analisar.')
    if amount>row['limit']:
        raise ValueError('Valor acima do crédito disponível para o porte e a dívida deste clube.')

def rate_premium(credit,bank,amount):
    if not credit:return 0
    limit=max(1,credit['banks'][str(bank)]['limit'])
    utilization=amount/limit
    prestige=max(0,min(20,int(credit['profile'].get('prestige') or 0)))
    return (0 if utilization<=.25 else 25 if utilization<=.5 else 60 if utilization<=.75 else 100)+(20-prestige)*3

def quote(credit,bank,amount,months):
    from loans import quote as base_quote
    return base_quote(bank,amount,months,extra_bps=rate_premium(credit,bank,amount))
