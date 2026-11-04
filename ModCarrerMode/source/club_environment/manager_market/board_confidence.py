"""Board trust combines expectations with the results of this appointment."""
import math

def for_spell(reviews,start,today,initial=False,stats=None):
 own=[r for r in reviews if start<=r['game_date']<=today and (initial or r['game_date']>start) and math.isfinite(r['pressure'])]
 if not own:return dict(value=75,pressure=None,date=0,label='Em avaliação',reason='Novo vínculo · aguardando avaliação desta passagem')
 review=max(own,key=lambda r:r['game_date']);performance=0
 if stats and stats.get('games',0)>0:
  performance=(max(0,min(100,stats['percentage']))-50)*.4*min(1,stats['games']/10)
 value=max(0,min(100,int(80-review['pressure']+performance+.5)))
 return dict(value=value,pressure=review['pressure'],date=review['game_date'],label='Confiança alta' if value>=80 else 'Moderada' if value>=60 else 'Baixa' if value>=40 else 'Muito baixa',reason=review['reason'])
