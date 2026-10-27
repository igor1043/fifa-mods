"""Bounded image uploads, background jobs, isolated persistent AI worker."""
from pathlib import Path
from PIL import Image,ImageOps,UnidentifiedImageError
from queue import Queue,Empty
import atexit,base64,binascii,hashlib,io,json,math,subprocess,sys,threading,time,uuid

ROOT=Path(__file__).resolve().parent
MAX_IMAGE=15*1024*1024
Image.MAX_IMAGE_PIXELS=24_000_000
class PoseService:
 def __init__(self):
  self.jobs={};self.lock=threading.Lock();self.work=threading.Lock();self.child=None;self.lines=None;self.idle=None;self.device=None;atexit.register(self.close)
 def info(self):
  ready=all((ROOT/'local_ai/models'/name).is_file() for name in ('rtmw3d.onnx','yolox.onnx','manifest.json'))
  return {'ready':ready,'model':'RTMW3D-X','landmarks':133,'local':True,'device':self.device,'max_people':48}
 def close(self):
  child=self.child;self.child=None
  if child:
   if child.poll() is None:child.kill()
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:pass
   for pipe in (child.stdin,child.stdout,child.stderr):
    if pipe:pipe.close()
 def _idle_close(self):
  if self.work.acquire(blocking=False):
   try:self.close()
   finally:self.work.release()
 def start(self,payload):
  if not self.info()['ready']:raise ValueError('Modelos locais indisponíveis. Execute local_ai/setup_models.py.')
  maximum=payload.get('max_people',11);confidence=payload.get('confidence',.45)
  if type(maximum) is not int or not 1<=maximum<=48:raise ValueError('Escolha de 1 a 48 pessoas.')
  if type(confidence) not in (int,float) or not math.isfinite(confidence) or not .2<=confidence<=.9:raise ValueError('Confiança do detector inválida.')
  encoded=payload.get('image','')
  if not isinstance(encoded,str) or len(encoded)>MAX_IMAGE*1.4:raise ValueError('Imagem muito grande; limite de 15 MB.')
  if not encoded.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):raise ValueError('Use uma imagem PNG, JPG ou WebP.')
  try:raw=base64.b64decode(encoded.split(',',1)[1],validate=True)
  except (binascii.Error,ValueError):raise ValueError('Imagem inválida.')
  if not 1<=len(raw)<=MAX_IMAGE:raise ValueError('Tamanho da imagem inválido.')
  if not self.work.acquire(blocking=False):raise BlockingIOError('Uma imagem já está sendo analisada.')
  try:
   identity=uuid.uuid4().hex;folder=ROOT/'imports'/identity;folder.mkdir(parents=True)
   try:
    with Image.open(io.BytesIO(raw)) as original:
     if original.format not in ('PNG','JPEG','WEBP') or original.width*original.height>24_000_000:raise ValueError('Imagem excede 24 megapixels.')
     image=ImageOps.exif_transpose(original).convert('RGB');image.thumbnail((3072,3072),Image.Resampling.LANCZOS);image.info.clear();image.save(folder/'input.png')
   except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ValueError('Não foi possível abrir a imagem.')
   regions=payload.get('regions',[])
   if not isinstance(regions,list) or len(regions)>48:raise ValueError('Recortes inválidos.')
   for box in regions:
    if not isinstance(box,list) or len(box)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in box) or not 0<=box[0]<box[2]<=image.width or not 0<=box[1]<box[3]<=image.height:raise ValueError('Recorte fora da imagem.')
   request={'image':str(folder/'input.png'),'name':str(payload.get('name','Imagem'))[:120],'max_people':maximum,'confidence':float(confidence),'regions':regions}
   with self.lock:
    if len(self.jobs)>=50:self.jobs.pop(next(iter(self.jobs)))
    self.jobs[identity]={'status':'working','message':'Preparando análise local…'}
   if self.idle:self.idle.cancel()
   threading.Thread(target=self._run,args=(identity,request,hashlib.sha256(raw).hexdigest()),daemon=True,name='image-pose-job').start()
   return identity
  except Exception:self.work.release();raise
 def status(self,identity):
  with self.lock:return self.jobs.get(identity,{}).copy()
 def _launch(self):
  if self.child is not None and self.child.poll() is None:return
  self.close();flags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)
  log=(ROOT/'local_ai/worker.log').open('ab')
  self.child=subprocess.Popen([sys.executable,'-B','-u',str(ROOT/'local_ai/worker.py')],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf8',creationflags=flags);log.close();self.lines=Queue(maxsize=128)
  stream=self.child.stdout;lines=self.lines
  def reader():
   try:
    for line in stream:
     try:lines.put(line,timeout=1)
     except Exception:break
   except (OSError,ValueError):pass
   finally:
    try:lines.put(None,timeout=1)
    except Exception:pass
  threading.Thread(target=reader,daemon=True,name='image-pose-output').start()
 def _run(self,identity,request,sha):
  try:
   self._launch();self.child.stdin.write(json.dumps(request)+'\n');self.child.stdin.flush();deadline=time.monotonic()+240
   while True:
    try:line=self.lines.get(timeout=max(.01,deadline-time.monotonic()))
    except Empty:raise TimeoutError('A análise demorou mais que o esperado. Tente um recorte menor.')
    if line is None:raise RuntimeError('O processo de IA encerrou. Consulte local_ai/worker.log.')
    if time.monotonic()>deadline:raise TimeoutError('A análise excedeu o limite de tempo.')
    try:result=json.loads(line)
    except ValueError:continue
    if result.get('status')=='error':raise RuntimeError(result.get('message','Falha na análise.'))
    if result.get('status')=='ready':
     capture=result['result'];capture['image'].update(sha256=sha,url=f'/imports/{identity}/input.png');self.device=capture['device']
     target=ROOT/'imports'/identity/'capture.json';target.write_text(json.dumps(capture,ensure_ascii=False,allow_nan=False),encoding='utf8')
     with self.lock:self.jobs[identity]={'status':'ready','message':f'{len(capture["people"])} pessoas detectadas.','capture':capture,'url':f'/imports/{identity}/capture.json'}
     break
    with self.lock:self.jobs[identity].update(message=str(result.get('message','Analisando…'))[:300])
  except Exception as error:
   self.close()
   with self.lock:self.jobs[identity]={'status':'error','message':str(error)}
  finally:
   self.work.release();self.idle=threading.Timer(90,self._idle_close);self.idle.daemon=True;self.idle.start()

service=PoseService()
