"""Read-only reporting joins. Native transactions never enter the mod payer."""


def categories(view,month=None):
 year=(view.get('date') or 0)//10000
 months=[r for r in view.get('months',[]) if r['month']//100==year and (month is None or r['month']==month)]
 total=lambda key:sum(r.get(key,0) for r in months)
 native=view.get('native_finance') or {}
 prize=native.get('prizes') if month is None else None
 buys=sales=loan_in=loan_out=0
 for t in view.get('transfers',[]):
  if t['date']//10000!=year or month is not None and t['date']//100!=month:continue
  if t.get('loan'):
   if t['direction']=='in':loan_in+=t['fee']
   else:loan_out+=t['fee']
  elif t['direction']=='in':buys+=t['fee']
  else:sales+=t['fee']
 row=lambda key,label,value,source,target:dict(key=key,label=label,value=value,source=source,target=target)
 revenues=[row('tv','Direitos de TV',total('tv'),'Mod · aplicado','tv'),
  row('ticket','Bilheteria bruta',total('tickets'),'Mod · aplicado','tickets'),
  row('sponsor','Patrocínio',total('sponsor'),'Mod · aplicado','sponsors'),
  row('members','Sócio-torcedor',total('members'),'Mod · aplicado','members'),
  row('transfer','Vendas de jogadores',sales,'Save · negócios confirmados','transfers:out'),
  row('prize','Premiações',prize,'Save · '+('valores confirmados' if prize is not None else 'histórico ainda indisponível'),'native'),
  row('loan','Empréstimos bancários',total('loan_credit'),'Financiamento · não é lucro','loans'),
  row('loan_players','Empréstimos de jogadores',loan_out,'Save · taxas confirmadas','transfers:out')]
 expenses=[row('coach','Salário do técnico',-total('coach'),'Mod · aplicado','expenses'),
  row('staff','Comissão técnica',-total('staff'),'Mod · aplicado','expenses'),
  row('match_costs','Operação dos jogos',-total('match_costs'),'Mod · aplicado','tickets'),
  row('facilities','Manutenção e estrutura',-total('facilities'),'Mod · aplicado','expenses'),
  row('transfer','Compras de jogadores',buys,'Save · negócios confirmados','transfers:in'),
  row('loan_players','Empréstimos de jogadores',loan_in,'Save · taxas confirmadas','transfers:in'),
  row('loan','Amortização de empréstimos',-total('loans')+total('interest'),'Principal · reduz dívida','loans'),
  row('interest','Juros dos empréstimos',-total('interest'),'Mod · aplicado','loans'),
  row('salary','Salários dos jogadores',native.get('player_wages') if month is None else None,'Save · total efetivo ainda indisponível','salaries'),
  row('prize','Bônus e premiações pagos',native.get('bonuses') if month is None else None,'Save · total efetivo ainda indisponível','native')]
 sort=lambda rows:sorted(rows,key=lambda r:(r['value'] is None,-(r['value'] or 0),r['label']))
 return dict(revenues=sort(revenues),expenses=sort(expenses),
  note='Extras do mod: pagos. Negócios do save: valores acordados; parcelamento nativo não identificado. Financiamento não é lucro.')


def composition(view,side,month=None):
 """Known operating categories only; principal/loan credit are financing."""
 key='revenues' if side=='receipts' else 'expenses'
 return [r for r in categories(view,month)[key] if r['key']!='loan' and r['value'] is not None and r['value']>0]


def period_months(view):
 year=(view.get('date') or 0)//10000;through=(view.get('date') or 0)//100
 found={r['month'] for r in view.get('months',[]) if r['month']//100==year and r['month']<=through}
 found|={r['date']//100 for r in view.get('transfers',[]) if r['date']//10000==year and r['date']//100<=through}
 if through:
  start=view.get('start') or year*10000+101
  first=start//100%100 if start//10000==year else 1
  found.update(year*100+m for m in range(max(1,first),through%100+1))
 return sorted(found,reverse=True)


def native_view(rows,*,club,season,today):
 """Unknown historical payments cannot be inferred from current wages/balance."""
 return dict(prizes=None,player_wages=None,bonuses=None,source='Save da carreira',club=club,season=season,date=today,
  reason='As tabelas de orçamento e contratos não contêm o extrato anual de pagamentos. Nenhuma premiação foi estimada por títulos ou saldo.')
