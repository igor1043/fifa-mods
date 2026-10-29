import json
from pathlib import Path
import tempfile
import unittest
from ui_theme import DEFAULTS, load, rgb, argb, rgba

class ThemeTests(unittest.TestCase):
    def test_missing_or_invalid_configuration_keeps_readable_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'theme.json'
            self.assertEqual(load(path),DEFAULTS)
            for raw in ('{', '[]', '{"version":2,"accent":"#000000"}'):
                path.write_text(raw);self.assertEqual(load(path),DEFAULTS)

    def test_configuration_reuses_the_same_hex_without_compilation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'theme.json'
            path.write_text(json.dumps(dict(version=1,accent='#abC123',accent_text='red')))
            tokens=load(path);self.assertEqual(tokens['accent'],'#ABC123')
            self.assertEqual(tokens['accent_text'],DEFAULTS['accent_text'])
            self.assertEqual(rgb(tokens['accent']),0xabc123)
            self.assertEqual(argb(tokens['accent']),0xffabc123)
            self.assertEqual(rgba(tokens['accent'],248),(171,193,35,248))

    def test_gold_selected_text_and_white_card_text_are_readable(self):
        def light(value):
            channels=rgba(value)[:3];v=[c/255 for c in channels]
            return sum(w*(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4) for w,x in zip((.2126,.7152,.0722),v))
        for foreground,background in [('accent_text','accent'),('accent_ink','surface')]:
            a,b=sorted((light(DEFAULTS[foreground]),light(DEFAULTS[background])))
            self.assertGreater((b+.05)/(a+.05),4.5)

if __name__=='__main__':
    unittest.main()
