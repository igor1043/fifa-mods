"""Build the native globe artwork (offline only; no network in the game).

Inputs: NASA BMNG October 2004 21600x10800 JPEG and Natural Earth v5.1.2
50m admin-0 GeoJSON. Dependencies for building: Pillow >=12, numpy, scipy.
Country IDs stay compatible with catalog.tsv; none of the FIFA icons are copied.
"""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

NASA = 'https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-topography-bathymetry/october/world.topo.bathy.200410.3x21600x10800.jpg'
COUNTRIES = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson'
SIZE = (8192, 4096)
DISTANCE_RANGE = 16


def earth_dds(source, destination):
    # Decode the actual higher-resolution source; never upscale the old 4K map.
    Image.MAX_IMAGE_PIXELS = 250_000_000
    with Image.open(source) as original:
        if original.width < SIZE[0] or original.height < SIZE[1]:
            raise ValueError('Earth source must be at least 8192x4096')
        image = original.convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)
    parts = []
    header = None
    while True:
        stream = io.BytesIO()
        image.save(stream, format='DDS', pixel_format='DXT1')
        blob = stream.getvalue()
        header = header or bytearray(blob[:128])
        parts.append(blob[128:])
        if image.size == (1, 1):
            break
        image = image.resize((max(1, image.width//2), max(1, image.height//2)), Image.Resampling.LANCZOS)
    struct.pack_into('<I', header, 8, struct.unpack_from('<I', header, 8)[0] | 0x20000)
    struct.pack_into('<I', header, 20, SIZE[0]*SIZE[1]//2)
    struct.pack_into('<I', header, 28, len(parts))
    struct.pack_into('<I', header, 108, 0x401008)  # TEXTURE | COMPLEX | MIPMAP
    destination.write_bytes(header + b''.join(parts))
    return len(parts)


def country_atlas(source, destination):
    features = json.loads(source.read_text(encoding='utf8'))['features']
    ids = json.loads(Path(__file__).with_name('globe_world_ids.json').read_text(encoding='utf8'))
    # The old 110m catalog groups these territories with their sovereign state.
    parents = {'US1':'USA','GB1':'GBR','FR1':'FRA','DN1':'DNK','NL1':'NLD',
               'NZ1':'NZL','AU1':'AUS','CH1':'CHN','FI1':'FIN'}
    countries = Image.new('L', SIZE)
    outlines = Image.new('L', SIZE)
    fill, line = ImageDraw.Draw(countries), ImageDraw.Draw(outlines)
    def points(ring):
        return [((lon+180)/360*SIZE[0]-.5, (90-lat)/180*SIZE[1]-.5) for lon,lat,*_ in ring]
    for feature in features:
        p, geometry = feature['properties'], feature['geometry']
        code = p['ADM0_A3']
        country = ids.get(code, ids.get(parents.get(p['SOV_A3'], ''), 255))
        polygons = geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        for polygon in polygons:
            for i, ring in enumerate(polygon):
                xy = points(ring)
                fill.polygon(xy, fill=country if i==0 else 0)
                # Distances, rather than a hard raster line, allow the shader to
                # keep a smooth ~one-pixel border at every zoom and latitude.
                line.line(xy, fill=255, width=1)
    distances = distance_transform_edt(np.asarray(outlines)==0)
    distances *= 255/DISTANCE_RANGE
    np.clip(distances, 0, 255, out=distances)
    field = Image.fromarray(np.rint(distances).astype('uint8'))
    # LA stores exact country IDs and the distance field independently. On the
    # GPU this becomes RG8: 64 MiB, half the memory of an 8K RGBA atlas.
    Image.merge('LA', (countries, field)).save(destination, optimize=True)


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    mips = earth_dds(source/'earth-21600.jpg', output/'earth.dds')
    country_atlas(source/'countries-50m.geojson', output/'atlas-hd.png')
    credits = dict(
        title='Blue Marble: Next Generation with Topography and Bathymetry, October 2004',
        credit='NASA Earth Observatory / Reto Stöckli', source=NASA,
        information='https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-topography-bathymetry/',
        processing=f'21600x10800 source downsampled to 8192x4096; BC1 DDS, {mips} mip levels.',
        boundaries=dict(credit='Made with Natural Earth', source=COUNTRIES,
                        information='https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2/',
                        license='Public domain', resolution=list(SIZE), distance_range=DISTANCE_RANGE,
                        processing='Exact country IDs (R), 16-texel unsigned distance field (G on GPU).'),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()},
    )
    (output/'earth-credits.json').write_text(json.dumps(credits,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({p.name:p.stat().st_size for p in output.iterdir()},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    build(args.source,args.output)
