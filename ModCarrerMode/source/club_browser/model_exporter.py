"""One isolated, persistent mesh exporter; bounded wait and explicit cleanup."""
from pathlib import Path
from queue import Queue,Empty
from threading import Thread
import subprocess,time

class ExportError(RuntimeError):
    """Keep native output available even when no model was produced."""
    def __init__(self,message,transcript='',exit_code=None):
        self.transcript=transcript;self.exit_code=exit_code
        super().__init__(message+(f' (exit={exit_code})' if exit_code is not None else ''))

class Exporter:
    def __init__(self):self.process=None;self.signature=None;self.lines=None
    def close(self):
        process=self.process;self.process=None;self.signature=None
        if process:
            if process.poll() is None:
                process.kill()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            if process.stdin:process.stdin.close()
    def run(self,tool,game,fixture,target,timeout=120,pose=1):
        if pose not in (1,401):raise ValueError('Modo de exportação inválido.')
        signature=(str(Path(game).resolve()),tool.stat().st_size,tool.stat().st_mtime_ns)
        if self.process and (self.process.poll() is not None or self.signature!=signature):self.close()
        if self.process is None:
            flags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'NORMAL_PRIORITY_CLASS',0)
            self.process=subprocess.Popen([str(tool),'--web-worker',str(game)],cwd=game,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=flags)
            self.signature=signature;self.lines=Queue(maxsize=128);stream=self.process.stdout;lines=self.lines
            def read():
                try:
                    for line in stream:
                        try:lines.put(line[:4096],timeout=1)
                        except Exception:break
                finally:
                    try:lines.put(None,timeout=1)
                    except Exception:pass
                    stream.close()
            Thread(target=read,daemon=True,name='FIFA-XI-export').start()
        transcript=[]
        try:
            self.process.stdin.write(f'{fixture}\t{target}\t{pose}\n');self.process.stdin.flush();deadline=time.monotonic()+timeout
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise ExportError('A preparação dos titulares excedeu o tempo limite.',''.join(transcript))
                try:line=self.lines.get(timeout=remaining)
                except Empty:raise ExportError('A preparação dos titulares excedeu o tempo limite.',''.join(transcript))
                if line is None:raise ExportError('O preparador dos titulares foi encerrado.',''.join(transcript),self.process.wait(timeout=5))
                transcript.append(line)
                if len(transcript)>128:transcript.pop(0)
                if line.startswith('FF_READY'):
                    if line.strip()!='FF_READY 0' or not Path(target).is_file():raise ExportError('Modelo 3D dos titulares indisponível.',''.join(transcript))
                    return ''.join(transcript)
        except Exception:self.close();raise
