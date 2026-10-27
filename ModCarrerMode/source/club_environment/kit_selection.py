"""Select the DB row for the matching year of the requested FIFA kit asset."""
def current_kits(rows,club):
 result={}
 for row in rows:
  if (row.get('teamtechid') or row.get('teamid'))!=club or row.get('year')!=0:continue
  typ=row['teamkittypetechid']
  if typ in result:
   # Modded databases can repeat a current type. Retain the first native
   # primary-key row instead of letting a later duplicate overwrite it.
   old=result[typ];a,b=old.get('teamkitid'),row.get('teamkitid')
   if isinstance(a,int) and isinstance(b,int) and a!=b:
    if a<b:continue
   elif old==row:continue
   else:raise ValueError('Uniforme atual ambíguo sem identificador de registro.')
  result[typ]=row
 return result
