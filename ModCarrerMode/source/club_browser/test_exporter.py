"""Exercise real child exit/output, rather than mocking the output queue."""
from pathlib import Path
import subprocess,sys,tempfile,unittest
from unittest.mock import patch
from model_exporter import Exporter,ExportError


class ExporterTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='XI export á ')
        self.root=Path(self.temp.name);self.fixture=self.root/'fixture.bin';self.fixture.write_bytes(b'fixture')
        self.target=self.root/'model.ff3d';self.exporter=Exporter()
        self.popen=subprocess.Popen

    def tearDown(self):
        self.exporter.close();self.temp.cleanup()

    def launch(self,body):
        def child(_command,**kwargs):
            return self.popen([sys.executable,'-X','utf8','-u','-c',body],**kwargs)
        return patch('model_exporter.subprocess.Popen',side_effect=child)

    def run_export(self,timeout=5):
        return self.exporter.run(Path(sys.executable),self.root,self.fixture,self.target,timeout=timeout)

    def test_native_crash_keeps_exit_code_and_last_diagnostic(self):
        with self.launch("import sys;print('Missing asset: jogador.rx3',flush=True);sys.exit(37)"):
            with self.assertRaises(ExportError) as caught:self.run_export()
        self.assertEqual(caught.exception.exit_code,37)
        self.assertIn('jogador.rx3',caught.exception.transcript)
        self.assertIn('exit=37',str(caught.exception))
        self.assertIsNone(self.exporter.process)

    def test_failed_request_keeps_output(self):
        with self.launch("print('Asset could not be decoded',flush=True);print('FF_READY 1',flush=True)"):
            with self.assertRaises(ExportError) as caught:self.run_export()
        self.assertIn('Asset could not be decoded',caught.exception.transcript)
        self.assertIn('FF_READY 1',caught.exception.transcript)

    def test_success_marker_without_model_is_rejected(self):
        with self.launch("print('FF_READY 0',flush=True)"):
            with self.assertRaises(ExportError):self.run_export()

    def test_success_reuses_child_for_second_request(self):
        body="from pathlib import Path\nimport sys\nfor line in sys.stdin:\n Path(line.split('\\t')[1]).write_bytes(b'model');print('FF_READY 0',flush=True)"
        with self.launch(body):
            self.assertIn('FF_READY 0',self.run_export())
            pid=self.exporter.process.pid
            self.assertIn('FF_READY 0',self.run_export())
            self.assertEqual(self.exporter.process.pid,pid)

    def test_timeout_terminates_child(self):
        with self.launch("import time;time.sleep(10)"):
            with self.assertRaises(ExportError):self.run_export(timeout=.1)
        self.assertIsNone(self.exporter.process)


if __name__=='__main__':unittest.main(verbosity=2)
