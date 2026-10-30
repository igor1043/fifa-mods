"""Delegate on-screen money to FIFA's own localization and selected currency.

Keep the integer accounting untouched. IDs 0/1/2 are game slots, not fixed
USD/EUR/GBP labels: a language/mod can relabel those slots to Real or Euro.
"""
from functools import lru_cache
import unicodedata

@lru_cache(maxsize=8)
def _labels(game,stamp):
    import json,subprocess
    from pathlib import Path
    from server16_py.fifa_db import _find_python32,_find_dll
    root=Path(game);cache=root/'ModCarrerMode/runtime/club_environment/bank/runtime/currency_labels.json'
    try:
        saved=json.loads(cache.read_text(encoding='utf8'))
        if saved.get('stamp')==list(stamp):return saved['labels']
    except (OSError,ValueError,KeyError):pass
    tool=_find_python32();dll=_find_dll()
    if tool is None or dll is None:return {}
    result=subprocess.run([str(tool),str(Path(__file__).with_name('currency_labels_worker.py')),str(dll),str(root/'data/loc/por_br.db'),str(root/'data/loc/por_br-meta.xml')],capture_output=True,check=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    labels=__import__('json').loads(result.stdout)
    cache.parent.mkdir(parents=True,exist_ok=True);temporary=cache.with_suffix('.new')
    temporary.write_text(json.dumps(dict(stamp=list(stamp),labels=labels),ensure_ascii=False),encoding='utf8');temporary.replace(cache)
    return labels

def currency_symbol(currency,labels=None,game=None):
    """Use the save's slot label, including patches which rename Dollar to Real."""
    if type(currency) is not int or currency not in (0,1,2):return ''
    if labels is None:
        try:
            from pathlib import Path
            import portable_paths
            root=Path(game or portable_paths.GAME);stat=(root/'data/loc/por_br.db').stat()
            labels=_labels(str(root),(stat.st_mtime_ns,stat.st_size))
        except (OSError,ValueError,RuntimeError,__import__('subprocess').SubprocessError):labels={}
    key=('CM_DollarCurrency','CM_EuroCurrency','CM_PoundsCurrency')[currency]
    name=unicodedata.normalize('NFKD',str(labels.get(key,''))).encode('ascii','ignore').decode().casefold()
    if any(word in name for word in ('real','reais','brl')):return 'R$'
    if any(word in name for word in ('euro','eur')):return '€'
    if any(word in name for word in ('dolar','dollar','usd')):return 'US$'
    if any(word in name for word in ('libra','pound','gbp')):return '£'
    return ''

def format_money(amount,currency=None,compact=False,*,symbol=None,labels=None):
    """Display the stored accounting integer; never apply an exchange rate."""
    value=int(amount);symbol=currency_symbol(currency,labels) if symbol is None else symbol
    if compact and abs(value)>=1000:
        scale,suffix=(1_000_000_000,' bi') if abs(value)>=1_000_000_000 else (1_000_000,' mi') if abs(value)>=1_000_000 else (1000,' mil')
        text=f'{abs(value)/scale:.1f}'.replace('.',',')+suffix
    else:text=f'{abs(value):,}'.replace(',','.')
    return ('−' if value<0 else '')+(symbol+' ' if symbol else '')+text

class MoneyText(str):
    def __new__(cls,text,expression):
        value=super().__new__(cls,text);value.expression=expression;return value
    def __add__(self,other):
        return MoneyText(str(self)+str(other),('bin',71,self.expression,expression(other)))
    def __radd__(self,other):
        return MoneyText(str(other)+str(self),('bin',71,expression(other),self.expression))

def expression(value):return value.expression if isinstance(value,MoneyText) else value

def native_money(amount,currency,call,path):
    text=f'{amount:,}'.replace(',','.')
    if type(currency) is not int or currency not in (0,1,2):return text
    # A single screen method owns the native binding. Calling it with one
    # integer keeps the compiled quote branches within the APT action budget.
    return MoneyText(text,call(('r',1),'FormatCareerMoney',amount))
