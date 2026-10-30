"""Bundle small bank logos into the APT; no network or image lookup in FIFA."""
from pathlib import Path
import io,struct,hashlib,os
from PIL import Image,ImageDraw
import portable_paths as portable
from formats import BigFile,AptFile
from loans import BANKS,OFFERED_BANKS

def validate_assets():
    """Exercise the same image encoder used by the native screen, while offline."""
    for index in OFFERED_BANKS:
        path=portable.GAME/'ModCarrerMode/data/club_environment/bank/assets'/(BANKS[index]['id']+'.png')
        with Image.open(path) as source:
            image=source.convert('RGBA');image.thumbnail((108,56))
        output=io.BytesIO();image.save(output,format='DDS',pixel_format='DXT5')
        if not output.getvalue().startswith(b'DDS '):raise ValueError('Imagem de banco inválida: '+str(path))
    return len(OFFERED_BANKS)

def texture_writer(data,append,new_chars,count,additions,character,cache=None):
    panel=AptFile(BigFile(portable.GAME/'data/ui/game/components/careercomponents/careerhubwidget.big'))
    cache=Path(cache) if cache is not None else None;encoded={}
    if cache is not None:cache.mkdir(parents=True,exist_ok=True)
    def write(image):
        width,height=image.size
        key=hashlib.sha256(struct.pack('<II',width,height)+image.convert('RGBA').tobytes()).hexdigest() if cache is not None else None
        if key in encoded:return encoded[key]
        target=cache/(key+'.dds') if cache is not None else None;dds=None
        if target is not None:
            try:
                raw=target.read_bytes()
                if len(raw)==128+((width+3)//4)*((height+3)//4)*16 and raw[:4]==b'DDS ' and struct.unpack_from('<II',raw,12)==(height,width) and raw[84:88]==b'DXT5':dds=bytearray(raw)
            except OSError:pass
        if dds is None:
            output=io.BytesIO();image.save(output,format='DDS',pixel_format='DXT5')
            dds=bytearray(output.getvalue());struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
            if target is not None:
                temporary=target.with_suffix('.'+str(os.getpid())+'.new');temporary.write_bytes(dds);os.replace(temporary,target)
        tex=count+len(new_chars);raw=bytearray(panel.data[panel.characters[1].offset:panel.characters[1].offset+40]);struct.pack_into('<I',raw,32,tex);character(raw);additions[str(tex+1)]=bytes(dds)
        ident=count+len(new_chars);raw=bytearray(panel.data[panel.characters[2].offset:panel.characters[2].offset+56]);struct.pack_into('<I',raw,16,tex<<16);struct.pack_into('<4fI',raw,32,0,0,width,height,ident);character(raw)
        geo=bytearray(panel.big.entries['3'].data[:96]);geo.extend(b''.join(struct.pack('<8f',x,y,0,0,0,0,0,0) for x,y in ((0,height),(0,0),(width,0),(width,0),(width,height),(0,height))))
        for offset,value in ((0,len(geo)),(16,len(geo)-16),(32,len(geo)-32),(52,tex)):struct.pack_into('<I',geo,offset,value)
        struct.pack_into('<6f',geo,64,1,0,0,1,0,0);additions[str(ident+1)]=bytes(geo)
        if key is not None:encoded[key]=ident
        return ident
    return write


def embed_logos(data,apt,append,new_chars,controls,count,additions,place,clip,character,write=None):
    write=write or texture_writer(data,append,new_chars,count,additions,character)
    for index,bank in enumerate(BANKS):
        path=portable.GAME/'ModCarrerMode/data/club_environment/bank/assets'/(bank['id']+'.png')
        image=Image.new('RGBA',(128,64),'white')
        if path.is_file():
            with Image.open(path) as source:logo=source.convert('RGBA')
            logo.thumbnail((108,56),Image.Resampling.LANCZOS)
            image.alpha_composite(logo,((128-logo.width)//2,(64-logo.height)//2))
        else:
            if index>=3:raise FileNotFoundError(path)
            ImageDraw.Draw(image).text((34,24),'BANCO',fill='#334b56')
        ident=write(image)
        controls.append(place(clip([place(ident,1,0,0)]),3000+index,650,350,.7,.7,name='bankLogo'+str(index)))
        controls.append(place(clip([place(ident,1,0,0)]),3100+index,695,320,1,.9,name='bankHeaderLogo'+str(index)))
