"""The board's trust is the inverse of the pressure used by dismissal reviews."""
import math

def for_spell(reviews,start,today,initial=False):
 # A dismissal/hire can share a date. That day's old review never belongs to
 # the newcomer. Initial appointments predate the market and have no predecessor.
 own=[r for r in reviews if start<=r['game_date']<=today and (initial or r['game_date']>start) and math.isfinite(r['pressure'])]
 if not own:return dict(value=75,pressure=None,date=0,label='Em avaliação',reason='Novo vínculo · aguardando avaliação desta passagem')
 review=max(own,key=lambda r:r['game_date']);value=max(0,min(100,int(100-review['pressure']+.5)))
 return dict(value=value,pressure=review['pressure'],date=review['game_date'],label='Confiança alta' if value>=80 else 'Moderada' if value>=60 else 'Baixa' if value>=40 else 'Muito baixa',reason=review['reason'])
