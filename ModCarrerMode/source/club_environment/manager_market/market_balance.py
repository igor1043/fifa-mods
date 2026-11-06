"""Bounded market decisions from the actual appointment's campaign."""
def dismissal_risk(raw,club,campaign):
 import unicodedata
 country=unicodedata.normalize('NFKD',str(club.get('country',''))).encode('ascii','ignore').decode().lower()
 brazil=country in ('brasil','brazil') or country.startswith(('brasil ','brazil '))
 games=campaign.get('games',0);percentage=campaign.get('percentage',0)
 if games<6:return 0
 if percentage>=65 or campaign.get('losses')==0:return 0
 if percentage>=50:
  # Only a very demanding club can exceptionally dismiss an otherwise
  # positive campaign; even then the ceiling is 0.25% per valid review.
  return min(raw,25) if club['reputation']>=8 and raw>=2500 else 0
 if brazil:
  # Brazil's higher raw pressure was previously cancelled by the global cap.
  # Keep football evidence/tenure gates; change only its regional risk curve.
  if percentage>=40:return min(raw,300+(50-percentage)*160)
  return min(raw,1900+4100*min(1,(40-percentage)/30))
 if percentage>=40:return min(raw,100+(50-percentage)*40)
 return min(raw,500+2500*min(1,(40-percentage)/30))

def reputation_delta(campaign,expected_percentage):
 if campaign.get('games',0)<6:return 0
 reliability=min(1,campaign['games']/20)
 return round(max(-.06,min(.06,(campaign['percentage']-expected_percentage)/100*.2))*reliability,4)
