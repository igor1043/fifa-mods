"""Check globe deployment, mip sizes, geographic IDs and outline precision."""
import csv
import json
import struct
import sys
from pathlib import Path
import numpy as np
from PIL import Image


def check(root):
    globe=root/'assets/globe'
    data=(globe/'earth.dds').read_bytes()
    assert data[:4]==b'DDS ' and struct.unpack_from('<I',data,84)[0]==0x31545844
    height,width=struct.unpack_from('<II',data,12)
    mips=struct.unpack_from('<I',data,28)[0]
    assert (width,height,mips)==(8192,4096,14)
    length=128
    for _ in range(mips):
        length+=max(1,(width+3)//4)*max(1,(height+3)//4)*8
        width,height=max(1,width//2),max(1,height//2)
    assert length==len(data), 'Truncated or extra mip data'
    with Image.open(globe/'atlas-hd.png') as image:
        assert image.mode=='LA' and image.size==(8192,4096)
        atlas=np.asarray(image)
    ids=set(np.unique(atlas[:,:,0]))
    with (root/'catalog.tsv').open(encoding='utf8') as source:
        for row in csv.reader(source,delimiter='\t'):
            assert int(row[3]) in ids, f'Missing country for {row[1]}'
    for lat,lon,expected in [(-15.8,-47.9,30),(48.8,2.35,44),(40,-100,5)]:
        assert atlas[int((90-lat)/180*4096),int((lon+180)/360*8192),0]==expected
    assert len(np.unique(atlas[:,:,1]))>64, 'Distance field became a hard binary edge'
    assert atlas[:,:,1].min()==0 and atlas[:,:,1].max()==255
    credit=json.loads((globe/'earth-credits.json').read_text(encoding='utf8'))
    assert credit['boundaries']['resolution']==[8192,4096]
    assert credit['boundaries']['distance_range']==16
    print('PASS globe assets: 8K BC1 / 14 mips, 8K RG atlas, all catalog countries, geographic IDs, smooth distances')


if __name__=='__main__':
    check(Path(sys.argv[1]))
