"""A clean release must reject stale embedded Server16 application modules."""
from pathlib import Path
import importlib.util
import tempfile
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('verify_frozen_release',ROOT/'ModCarrerMode/tools/Verify-PortablePackage.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)


class FrozenReleaseSources(unittest.TestCase):
    def fixture(self,root,stale=None):
        modules={}
        for module in verify.FROZEN_SOURCE_MODULES:
            path=root/Path(*module.split('.')).with_suffix('.py')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(b'CURRENT_REVISION = 2\n')
            raw=b'CURRENT_REVISION = 1\n' if module==stale else path.read_bytes()
            modules[module]=compile(raw,module.replace('.','/')+'.py','exec',optimize=0)
        return SimpleNamespace(extract=modules.__getitem__)

    def test_all_current_modules_match(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=self.fixture(root)
            self.assertEqual(verify.check_frozen_sources(archive,root),list(verify.FROZEN_SOURCE_MODULES))

    def test_rejects_stale_application_even_when_loose_source_is_current(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=self.fixture(root,'server16_py.app')
            with self.assertRaisesRegex(AssertionError,'server16_py.app'):
                verify.check_frozen_sources(archive,root)

    def test_rejects_stale_asset_permission_module(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=self.fixture(root,'server16_py.file_tools')
            with self.assertRaisesRegex(AssertionError,'server16_py.file_tools'):
                verify.check_frozen_sources(archive,root)

    def test_rejects_stale_stadium_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=self.fixture(root,'server16_py.stadium_runtime')
            with self.assertRaisesRegex(AssertionError,'server16_py.stadium_runtime'):
                verify.check_frozen_sources(archive,root)


if __name__=='__main__':unittest.main()
