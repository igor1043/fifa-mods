"""Actual local inference: single person, crowd, manual crop and empty image."""
from pathlib import Path
import base64,json,sys,time
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from pose_service import service
def analyze(path,**settings):
 payload={'image':'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode(),'name':path.name,'max_people':16,'confidence':.35,**settings}
 start=time.monotonic();identity=service.start(payload)
 while time.monotonic()-start<245:
  result=service.status(identity)
  if result['status']=='error':raise RuntimeError(result['message'])
  if result['status']=='ready':return result['capture']
  time.sleep(.2)
 raise TimeoutError()
cases=[]
try:
 image=Image.open(ROOT/'reference.png');single=ROOT/'build/tests/person-single.png';image.crop((145,10,312,595)).save(single)
 for name,path,settings,wanted in [('single',single,{'max_people':1},1),('multiple',ROOT/'reference.png',{},11),('manual',ROOT/'reference.png',{'regions':[[145,10,312,595]],'max_people':1},1)]:
  result=analyze(path,**settings);assert len(result['people'])==wanted,(name,len(result['people']));assert all(len(p['keypoints3d'])==133 for p in result['people']);cases.append({'case':name,'people':len(result['people']),'device':result['device'],'seconds':result['seconds']});print(json.dumps(cases[-1]),flush=True)
 blank=ROOT/'build/tests/empty-image.png';Image.new('RGB',(640,480),'black').save(blank);result=analyze(blank);assert result['people']==[];cases.append({'case':'empty','people':0,'seconds':result['seconds']})
 (ROOT/'build/tests/ai-inference-validation.json').write_text(json.dumps({'actual_inference':True,'cases':cases,'images_uploaded_to_external_service':False},indent=2));print('ALL_AI_CASES_PASS',flush=True)
finally:service.close()
