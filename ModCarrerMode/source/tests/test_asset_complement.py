"""The full external complement must close every declared asset dependency."""
from pathlib import Path, PurePosixPath
import importlib.util
import json
import sqlite3
import unittest

ROOT=Path(__file__).resolve().parents[3]


class AssetComplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'ModCarrerMode/data/catalogs/asset_complement.json').read_text(encoding='utf8'))
        cls.rows={r['path']:r for r in cls.manifest['files']}

    def test_unique_safe_paths_and_no_personal_databases(self):
        self.assertEqual(self.manifest['schema'],1)
        self.assertEqual(len(self.rows),len(self.manifest['files']))
        self.assertEqual(len({p.casefold() for p in self.rows}),len(self.rows))
        for name,row in self.rows.items():
            path=PurePosixPath(name)
            self.assertFalse(path.is_absolute())
            self.assertNotIn('..',path.parts)
            self.assertNotIn(':',name)
            self.assertNotIn('\\',name)
            self.assertFalse(name.startswith(('ModCarrerMode/runtime/','ModCarrerMode/cache/','runtime/','outputs/')))
            self.assertNotIn(path.suffix.lower(),('.sqlite','.sqlite3','.log','.dmp','.exe','.dll','.py'))
            if path.suffix.lower()=='.db':self.assertEqual(name,'data/loc/por_br.db')
            self.assertGreater(row['bytes'],0)
            self.assertEqual(len(row['sha256']),64)

    def test_original_module_dependencies_are_in_zip_or_in_source_payload(self):
        for relative in ('ModCarrerMode/source/club_environment/assets-manifest.json',
                         'ModCarrerMode/data/club_browser/assets-manifest.json',
                         'ModCarrerMode/data/catalogs/presentation_assets.json'):
            for row in json.loads((ROOT/relative).read_text(encoding='utf8'))['files']:
                if row['path'] in self.rows:
                    self.assertEqual(row['sha256'],self.rows[row['path']]['sha256'])
                    self.assertEqual(row['bytes'],self.rows[row['path']]['bytes'])
                else:
                    # A small animation JSON is already versioned with its code.
                    self.assertEqual(Path(row['path']).suffix,'.json')
                    self.assertTrue((ROOT/row['path']).is_file())

    def test_pose_subson_coach_faces_and_all_scoreboard_copy_sources_are_present(self):
        for relative in ('ModCarrerMode/data/club_browser/poses/starting_eleven.pose',
                         'data/ant.cbac','data/fifarna/splash.fsh',
                         'ModCarrerMode/data/manager_market/minifaces/NOTFOUND_DEFAULT.png',
                         'data/ui/game/globalcomponents/globalcomponents.big',
                         'FSW/ScoreBoard/globalcomponents/globalcomponents.big',
                         'ScoreBoardGBD/XXX - EI Maxx CN/game/globalcomponents/globalcomponents.big'):
            self.assertIn(relative,self.rows)
        sources=[row['sha256'] for name,row in self.rows.items() if name.endswith('/globalcomponents/globalcomponents.big')]
        self.assertEqual(len(sources),3)
        self.assertEqual(len(set(sources)),1)
        self.assertEqual(sum('/manager_market/minifaces/' in name for name in self.rows),
                         self.manifest['groups']['manager_minifaces'])
        self.assertFalse(any('/var_room/' in name for name in self.rows))
        self.assertTrue(any('/var_cabin/' in name for name in self.rows))

    def test_public_coach_catalog_has_all_referenced_photos_in_the_complement(self):
        path=ROOT/'ModCarrerMode/data/manager_market/catalog.sqlite3'
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            images={row[0] for row in db.execute('select image from coaches') if row[0]}
        for image in images:
            self.assertNotIn('..',PurePosixPath(image).parts)
            self.assertIn('ModCarrerMode/data/manager_market/'+image,self.rows)

    def test_public_packager_reads_the_complete_manifest(self):
        spec=importlib.util.spec_from_file_location('full_asset_builder',ROOT/'ModCarrerMode/tools/Build-PortablePackages.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.asset_rows(ROOT),self.manifest['files'])


if __name__=='__main__':unittest.main()
