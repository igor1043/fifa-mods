"""Fetch published inference assets once; user images never leave the PC."""
from pathlib import Path
import hashlib,json,os,urllib.request,zipfile,time
ROOT=Path(__file__).resolve().parent
MODELS=ROOT/'models';MODELS.mkdir(exist_ok=True)
SOURCES={
 'rtmw3d.onnx':('https://huggingface.co/Soykaf/RTMW3D-x/resolve/main/onnx/rtmw3d-x_8xb64_cocktail14-384x288-b0a0eab7_20240626.onnx',369330857),
 'yolox.zip':('https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/yolox_m_8xb8-300e_humanart-c2c7a14a.zip',94223081)
}
report={'models':{},'reference':'https://github.com/Tau-J/rtmlib/blob/main/rtmlib/tools/solution/wholebody3d.py'}
for name,(url,expected) in SOURCES.items():
 target=MODELS/name
 if not target.is_file() or target.stat().st_size!=expected:
  partial=target.with_suffix(target.suffix+'.partial');done=0;last=0
  with urllib.request.urlopen(url,timeout=60) as response,partial.open('wb') as output:
   while chunk:=response.read(1024*1024):
    output.write(chunk);done+=len(chunk)
    if time.monotonic()-last>5:print(name,round(done/expected*100),'%',flush=True);last=time.monotonic()
  if partial.stat().st_size!=expected:raise ValueError('Model download incomplete: '+name)
  os.replace(partial,target)
 report['models'][name]={'url':url,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
 if name.endswith('.zip'):
  with zipfile.ZipFile(target) as archive:
   names=[n for n in archive.namelist() if n.endswith('.onnx')]
   if len(names)!=1:raise ValueError('Unexpected detector archive')
   destination=MODELS/'yolox.onnx'
   if not destination.is_file():destination.write_bytes(archive.read(names[0]))
(MODELS/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('MODELS_READY',flush=True)
