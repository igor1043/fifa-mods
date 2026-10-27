from pathlib import Path
import base64,json,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent;BASE='http://127.0.0.1:'+ (ROOT/'server.port').read_text().strip()
def call(path,data=None,origin=None):
 headers={'Content-Type':'application/json'}
 if origin:headers['Origin']=origin
 request=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
 try:
  with urllib.request.urlopen(request,timeout=20) as response:return response.status,response.read()
 except urllib.error.HTTPError as response:return response.code,response.read()
status,raw=call('/api/pose');assert status==200 and json.loads(raw)['ready']
status,raw=call('/api/pose/missing');assert status==404
status,raw=call('/api/pose',{},origin='https://example.invalid');assert status==403
status,raw=call('/api/pose',{'image':'https://example.invalid/x.png'});assert status==400
for path in ('/index.html','/image_pose_ui.js','/image_pose.css','/pose_capture.js','/pose_retarget.js'):
 status,raw=call(path);assert status==200 and len(raw)>100,path
payload={'image':'data:image/png;base64,'+base64.b64encode((ROOT/'build/tests/person-single.png').read_bytes()).decode(),'max_people':1,'confidence':.35,'name':'single test'}
status,raw=call('/api/pose',payload);assert status==202,raw;identity=json.loads(raw)['id'];status,raw=call('/api/pose',payload);assert status==409
start=time.monotonic()
while time.monotonic()-start<240:
 status,raw=call('/api/pose/'+identity);assert status==200;job=json.loads(raw)
 if job['status']=='error':raise RuntimeError(job['message'])
 if job['status']=='ready':break
 status,raw=call('/index.html');assert status==200;time.sleep(.2)
else:raise TimeoutError()
assert len(job['capture']['people'])==1;status,raw=call(job['url']);assert status==200 and json.loads(raw)['type']=='fifa-friends-pose-capture'
report={'api':'passed','actual_inference':True,'people':1,'device':job['capture']['device'],'seconds':round(time.monotonic()-start,2),'server_responsive_during_inference':True}
(ROOT/'build/tests/ai-http-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
