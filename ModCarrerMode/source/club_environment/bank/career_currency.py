"""Delegate on-screen money to FIFA's own localization and selected currency.

Keep the integer accounting untouched. IDs 0/1/2 are game slots, not fixed
USD/EUR/GBP labels: a language/mod can relabel those slots to Real or Euro.
"""
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
