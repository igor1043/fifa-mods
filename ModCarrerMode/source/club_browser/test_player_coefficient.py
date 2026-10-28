"""Integration checks using FIFA's real RX3 payload and an exported player."""
from pathlib import Path
import hashlib,json,struct,tempfile,unittest
from unittest.mock import patch
import native_assets
from native_assets import Rx3,TEXTURE,player_coefficient,convert
import portable_paths


class PlayerCoefficientTests(unittest.TestCase):
    def test_original_coefficients_and_all_mips_are_byte_identical(self):
        original=portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3')
        rx=Rx3(original);names=[n for k,n in rx.names() if k==TEXTURE]
        expected=rx.get(TEXTURE)[names.index('prop_coeff')]
        generated=Rx3(player_coefficient(original))
        self.assertEqual(generated.names(),[(TEXTURE,'xi_coeff')])
        self.assertEqual(generated.get(TEXTURE),[expected])
        self.assertEqual(struct.unpack_from('<4H',expected,8),(128,128,1,8))
        self.assertEqual(original,portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'))

    def test_player_and_static_scene_keep_geometry_and_colour_textures_identical(self):
        model=Path(__file__).resolve().parents[3]/'code-release/club_roster_r3_20261027/player-static.ff3d'
        if not model.is_file():self.skipTest('Local exported-player integration fixture unavailable')
        with tempfile.TemporaryDirectory(prefix='native-coefficient-test-') as temp:
            a=Path(temp)/'static';b=Path(temp)/'actor'
            convert(model,a,portable_paths.read_asset)
            convert(model,b,portable_paths.read_asset,animated=True)
            self.assertEqual(sorted(p.name for p in a.iterdir()),sorted(p.name for p in b.iterdir()))
            for file in a.iterdir():
                if file.name in ('neutral_coeff.rx3','assets.json'):continue
                self.assertEqual(file.read_bytes(),(b/file.name).read_bytes(),file.name)
            self.assertNotEqual((a/'neutral_coeff.rx3').read_bytes(),(b/'neutral_coeff.rx3').read_bytes())
            template=portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3')
            self.assertEqual((b/'neutral_coeff.rx3').read_bytes(),player_coefficient(template))
            self.assertEqual(json.loads((b/'assets.json').read_text())['player_coefficient'],'native_payload_all_mips_v1')
            self.assertNotIn('player_coefficient',json.loads((a/'assets.json').read_text()))


if __name__=='__main__':unittest.main()
