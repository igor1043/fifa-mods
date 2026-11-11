import copy,json,tempfile,unittest
from pathlib import Path
from room_pes_office import PREFIX,model_path,obstacles,prepare


class ImportedOfficeTests(unittest.TestCase):
    def test_missing_optional_pack_keeps_existing_room(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(model_path(root,'original.rx3'),'original.rx3')
            self.assertFalse(prepare(root,lambda *a,**k:self.fail('unexpected prop'),[]))

    def test_only_listed_assets_and_old_furniture_are_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/PREFIX;folder.mkdir(parents=True)
            (folder/'office.json').write_text(json.dumps(dict(replacements={'old.rx3':'new.rx3'},bindings=[],obstacles=[dict(name='PES office / desk',lo=[1,0,2],hi=[2,80,3])])),encoding='utf8')
            items=[dict(name='Sala do treinador R76 / mesa'),dict(name='Sala do treinador R76 / parede'),dict(name='Salas / portas abertas'),dict(name='Departamento médico / mesa')];saved=copy.deepcopy(items)
            self.assertEqual(model_path(root,'old.rx3'),'new.rx3')
            self.assertEqual(model_path(root,'unrelated.rx3'),'unrelated.rx3')
            result=obstacles(root,items)
            self.assertEqual(items,saved)
            self.assertEqual([r['name'] for r in result],['Sala do treinador R76 / parede','Salas / portas abertas','Departamento médico / mesa','PES office / desk'])

    def test_preserves_binding_material_and_assembly_matrix(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/PREFIX;folder.mkdir(parents=True)
            (folder/'office.json').write_text(json.dumps(dict(bindings=[dict(key='chair',model='chair.rx3',texture='chair-texture.rx3',alpha=True,submesh='chair')])));calls=[];matrix=list(range(16))
            self.assertTrue(prepare(root,lambda *a,**k:calls.append(a),matrix))
            self.assertEqual(calls,[('chair','chair.rx3','chair-texture.rx3','office_cm',matrix,True,'chair')])


if __name__=='__main__':unittest.main()
