from pathlib import Path
import base64,json,sys,time
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from pose_service import service
payload={'image':'data:image/png;base64,'+base64.b64encode((ROOT/'reference.png').read_bytes()).decode(),'name':'reference.png','max_people':16,'confidence':.35}
identity=service.start(payload);last=None;begin=time.monotonic()
try:
 while time.monotonic()-begin<245:
  result=service.status(identity)
  if result.get('message')!=last:print(result.get('message'),flush=True);last=result.get('message')
  if result.get('status')=='error':raise RuntimeError(result['message'])
  if result.get('status')=='ready':
   capture=result['capture'];(ROOT/'build/tests/ai-reference.json').write_text(json.dumps(capture,indent=2),encoding='utf8');print(json.dumps({'people':len(capture['people']),'device':capture['device'],'seconds':capture['seconds'],'total':round(time.monotonic()-begin,2),'confidences':[p['confidence'] for p in capture['people']]}),flush=True);break
  time.sleep(.3)
 else:raise TimeoutError()
finally:service.close()
