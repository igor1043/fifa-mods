"""Verify the running editor API, including a real full-team background export."""
from pathlib import Path
import json,time,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:'+ (ROOT/'server.port').read_text().strip()
def request(path,data=None,origin=None,raw=None):
    headers={}
    if data is not None:raw=json.dumps(data,allow_nan=False).encode();headers['Content-Type']='application/json'
    if origin:headers['Origin']=origin
    req=urllib.request.Request(BASE+path,data=raw,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=20) as response:return response.status,response.read(),response.headers
    except urllib.error.HTTPError as response:return response.code,response.read(),response.headers

code,body,_=request('/api/health');assert code==200 and json.loads(body)['schema']==2
code,body,_=request('/api/export/not-an-export');assert code==404
code,body,_=request('/api/export',data={'schema':2},origin='https://example.invalid');assert code==403
code,body,_=request('/api/export',data={'schema':99});assert code==400
for path in ('/index.html','/scene.html','/scene_editor.js','/scene_view.js','/fifa_model.js','/vendor/three/build/three.module.js'):
    code,body,headers=request(path);assert code==200 and len(body)>100,path

scene=json.loads((ROOT/'build/tests/baseline-scene.json').read_text(encoding='utf8'))
code,body,_=request('/api/export',data=scene);assert code==202,body;identity=json.loads(body)['id']
code,body,_=request('/api/export',data=scene);assert code==409,body
start=time.monotonic()
while time.monotonic()-start<90:
    code,body,_=request('/api/export/'+identity);assert code==200
    result=json.loads(body)
    if result['status']=='error':raise RuntimeError(result['message'])
    if result['status']=='ready':break
    # The static UI stays available while the native export runs.
    code,body,_=request('/index.html');assert code==200
    time.sleep(.15)
else:raise TimeoutError('Native export did not finish.')
code,body,_=request(result['url']);assert code==200 and body[:2]==b'PK'
report={'api':'passed','actors':len(scene['actors']),'files':result['files'],'zip_bytes':len(body),'seconds':round(time.monotonic()-start,2),'export_url':BASE+result['url']}
(ROOT/'build/tests/http-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
