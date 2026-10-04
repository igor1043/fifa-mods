"""Decode installed DDS banners for visual material QA; never alter game assets."""
from pathlib import Path
from PIL import Image, ImageDraw

names = ('_Betano', 'adidasbig', 'cladidas', 'adidas3logos', 'CocaColaa', 'Hyundai', '_Penalty')
sheet = Image.new('RGB', (550, len(names) * 96), 'white')
draw = ImageDraw.Draw(sheet)
for row, name in enumerate(names):
    path = Path('U:/fifa 16/data/ui/imgAssets/adsponsors512x64') / ('adsponsors512x64' + name + '.dds')
    draw.text((8, row * 96), name, fill='black')
    with Image.open(path) as source:
        sheet.paste(source.convert('RGB'), (8, row * 96 + 20))
sheet.save(Path(__file__).parent / 'resultados' / 'patrocinios-nativos-inspecao.png')
