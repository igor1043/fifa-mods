"""Local editor and bounded background exports. Never installs into FIFA."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse
import argparse, functools, json, threading, uuid

ROOT=Path(__file__).resolve().parent
JOBS={};LOCK=threading.Lock();EXPORT_LOCK=threading.Lock()

def run_export(identity,scene):
    def progress(message):
        with LOCK:JOBS[identity]['message']=message
    try:
        from scene_export import export_package
        config=ROOT/'settings.json'
        if not config.is_file():raise ValueError('Execute Configurar FIFA.cmd e escolha a pasta do jogo para exportar RX3. Editar e salvar JSON não exigem essa configuração.')
        settings=json.loads(config.read_text(encoding='utf-8-sig'))
        if not settings.get('game_root'):raise ValueError('Escolha a pasta do jogo em Configurar FIFA.cmd antes de exportar RX3.')
        result=export_package(scene,ROOT/'exports'/identity,settings['game_root'],progress)
        with LOCK:JOBS[identity].update(status='ready',message='Cena exportada. Nenhum arquivo foi instalado no jogo.',url=f'/exports/{identity}/cena-fifa.zip',files=result['files'])
    except Exception as error:
        import traceback;traceback.print_exc()
        with LOCK:JOBS[identity].update(status='error',message=str(error))
    finally:EXPORT_LOCK.release()

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
    def log_message(self,*args):pass
    def json_response(self,code,value):
        raw=json.dumps(value,ensure_ascii=False).encode('utf8');self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.valid_host():return self.json_response(403,{'error':'Acesso somente local.'})
        path=urlparse(self.path).path
        if path=='/api/health':return self.json_response(200,{'application':'fifa-friends-scene-editor','schema':2})
        if path=='/api/pose':
            from pose_service import service
            return self.json_response(200,service.info())
        if path.startswith('/api/pose/'):
            from pose_service import service
            value=service.status(path.removeprefix('/api/pose/'))
            return self.json_response(200 if value else 404,value or {'error':'Análise não encontrada.'})
        if path.startswith('/api/export/'):
            identity=path.removeprefix('/api/export/')
            with LOCK:value=JOBS.get(identity,{}).copy()
            return self.json_response(200 if value else 404,value or {'error':'Exportação não encontrada.'})
        super().do_GET()
    def do_POST(self):
        origin=self.headers.get('Origin');allowed=(f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}')
        if not self.valid_host() or (origin and origin not in allowed):return self.json_response(403,{'error':'Exportação disponível apenas nesta bancada local.'})
        if self.path not in ('/api/export','/api/pose'):return self.json_response(404,{'error':'Comando não encontrado.'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.json_response(415,{'error':'Envie uma cena JSON.'})
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:length=0
        limit=22 if self.path=='/api/pose' else 20
        if not 0<length<=limit*1024*1024:return self.json_response(413,{'error':'Arquivo excede o limite da operação.'})
        self.connection.settimeout(20)
        try:
            scene=json.loads(self.rfile.read(length))
            if not isinstance(scene,dict) or (self.path=='/api/export' and scene.get('schema')!=2):raise ValueError()
        except (ValueError,TimeoutError):return self.json_response(400,{'error':'Cena JSON inválida.'})
        if self.path=='/api/pose':
            from pose_service import service
            try:return self.json_response(202,{'id':service.start(scene)})
            except ValueError as error:return self.json_response(400,{'error':str(error)})
            except BlockingIOError as error:return self.json_response(409,{'error':str(error)})
        if not EXPORT_LOCK.acquire(blocking=False):return self.json_response(409,{'error':'Já existe uma exportação em andamento.'})
        identity=uuid.uuid4().hex
        with LOCK:
            if len(JOBS)>=100:JOBS.pop(next(iter(JOBS)))
            JOBS[identity]={'status':'working','message':'Validando a cena…'}
        threading.Thread(target=run_export,args=(identity,scene),daemon=True,name='scene-export').start()
        self.json_response(202,{'id':identity})

if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('--port',type=int,default=0);options=args.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',options.port),functools.partial(Handler,directory=str(ROOT)))
    (ROOT/'server.port').write_text(str(server.server_port),encoding='ascii')
    print(f'http://127.0.0.1:{server.server_port}/scene.html',flush=True)
    server.serve_forever()
