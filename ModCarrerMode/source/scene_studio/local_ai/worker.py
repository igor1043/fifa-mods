"""Isolated local ONNX inference. Only fixed, already-downloaded models load."""
from pathlib import Path
import json,os,sys,time,traceback
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
os.environ.setdefault('OMP_NUM_THREADS','4')
import cv2
import numpy as np
import onnxruntime as ort
from rtmlib import YOLOX,RTMPose3d

def emit(value):print(json.dumps(value,ensure_ascii=True,allow_nan=False),flush=True)
def session(path,gpu=False):
 options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1;options.enable_mem_pattern=False;options.enable_cpu_mem_arena=False;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL;options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC;options.log_severity_level=3
 providers=['CPUExecutionProvider']
 if gpu and 'DmlExecutionProvider' in ort.get_available_providers():
  device=json.loads((ROOT/'device.json').read_text()) if (ROOT/'device.json').is_file() else {'device_id':0}
  providers=[('DmlExecutionProvider',{'device_id':str(device['device_id'])}),'CPUExecutionProvider']
 try:return ort.InferenceSession(str(path),sess_options=options,providers=providers)
 except Exception:
  if len(providers)==1:raise
  return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])

class Detector(YOLOX):
 def __init__(self):
  self.session=session(ROOT/'models/yolox.onnx');self.model_input_size=(640,640);self.backend='onnxruntime';self.mean=self.std=None;self.det_mode='human';self.nms_thr=.55;self.score_thr=.45
class Pose(RTMPose3d):
 def __init__(self):
  self.session=session(ROOT/'models/rtmw3d.onnx',True);self.model_input_size=(288,384);self.backend='onnxruntime';self.mean=(123.675,116.28,103.53);self.std=(58.395,57.12,57.375);self.to_openpose=False;self.z_range=2.1744869

class Engine:
 def __init__(self):
  emit({'status':'progress','message':'Carregando detector local de pessoas…'});self.detector=Detector()
  emit({'status':'progress','message':'Carregando RTMW3D para corpo, mãos e pés…'});self.pose=Pose()
  self.device='DirectML' if 'DmlExecutionProvider' in self.pose.session.get_providers() else 'CPU'
 def detect(self,request):
  began=time.perf_counter();path=Path(request['image']).resolve();allowed=(ROOT.parent/'imports').resolve();path.relative_to(allowed)
  # OpenCV's Windows filename API can reject accents; Python opens Unicode paths.
  image=cv2.imdecode(np.frombuffer(path.read_bytes(),dtype=np.uint8),cv2.IMREAD_COLOR)
  if image is None:raise ValueError('Imagem indisponível.')
  height,width=image.shape[:2];self.detector.score_thr=request['confidence']
  regions=request.get('regions')
  emit({'status':'progress','message':'Localizando as pessoas na imagem…'})
  boxes=np.array(regions,dtype=np.float32) if regions else self.detector(image)
  boxes=sorted(boxes,key=lambda b:float((b[2]-b[0])*(b[3]-b[1])),reverse=True)[:request['max_people']]
  people=[]
  for i,box in enumerate(boxes):
   box=np.clip(np.asarray(box,float),[0,0,0,0],[width,height,width,height]);left,top,right,bottom=box
   if right-left<12 or bottom-top<24:continue
   emit({'status':'progress','message':f'Estimando esqueleto 3D · {i+1} de {len(boxes)}','current':i+1,'total':len(boxes)})
   points,scores,_,pixels=self.pose(image,bboxes=[box]);points=points[0];scores=np.clip(scores[0],0,1);pixels=pixels[0]
   if points.shape!=(133,3) or not np.isfinite(points).all() or not np.isfinite(pixels).all():continue
   hip=pixels[[11,12]].mean(axis=0);hip_z=points[[11,12],2].mean();scale=1.75/max(float(bottom-top),64)
   world=np.column_stack(((pixels[:,0]-hip[0])*scale,-(pixels[:,1]-hip[1])*scale,-np.clip(points[:,2]-hip_z,-1.5,1.5)))
   confidence=float(scores[:17].mean())
   if confidence<.12 or int((scores[:17]>.15).sum())<5:continue
   people.append({'id':f'person-{i+1}','bbox':box.round(3).tolist(),'confidence':round(confidence,5),'keypoints2d':np.column_stack((pixels,scores)).round(6).tolist(),'keypoints3d':np.column_stack((world,scores)).round(6).tolist(),'meters_per_pixel':scale})
  # Stable, image-space ordering; the user can change every actor assignment.
  people.sort(key=lambda p:(round(p['bbox'][1]/max(1,height)*4),p['bbox'][0]))
  for i,p in enumerate(people):p['id']=f'person-{i+1}'
  return {'schema':1,'type':'fifa-friends-pose-capture','image':{'width':width,'height':height,'name':request.get('name','Imagem')},'model':'RTMW3D-X / COCO-WholeBody 133','device':self.device,'coordinates':'view-aligned meters, hip-centered; estimated depth','people':people,'seconds':round(time.perf_counter()-began,3)}

engine=None
for line in sys.stdin:
 try:
  request=json.loads(line)
  if engine is None:engine=Engine()
  result=engine.detect(request);emit({'status':'ready','result':result})
 except Exception as error:
  traceback.print_exc(file=sys.stderr);emit({'status':'error','message':str(error)})
