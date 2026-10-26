"""FIFA 16 BIG, chunkref (RefPack), and chunkzip (raw DEFLATE)."""
import struct
import zlib

LIMIT = 512*1024*1024


def refpack(src):
    if src[:2] != b'\x10\xfb': raise ValueError('RefPack não suportado')
    size=int.from_bytes(src[2:5],'big')
    if not 0 < size <= LIMIT: raise ValueError('Tamanho RefPack inválido')
    out=bytearray();p=5
    while p<len(src):
        a=src[p];p+=1
        if a < 0x80:
            lit=a&3;copy=((a>>2)&7)+3;back=((a&0x60)<<3)+src[p]+1;p+=1
        elif a < 0xc0:
            b,c=src[p:p+2];p+=2;lit=b>>6;copy=(a&63)+4;back=((b&63)<<8)+c+1
        elif a < 0xe0:
            b,c,d=src[p:p+3];p+=3;lit=a&3;copy=((a&12)<<6)+d+5;back=((a&16)<<12)+(b<<8)+c+1
        elif a < 0xfc:
            lit=((a&31)<<2)+4;copy=0;back=0
        else:
            out.extend(src[p:p+(a&3)]);break
        if p+lit>len(src): raise ValueError('RefPack truncado')
        out.extend(src[p:p+lit]);p+=lit
        if copy:
            if back>len(out): raise ValueError('Referência RefPack inválida')
            start=len(out)-back
            if back>=copy: out.extend(out[start:start+copy])
            else:
                pattern=out[start:];out.extend((pattern*((copy+back-1)//back))[:copy])
        if len(out)>size: raise ValueError('RefPack excedeu tamanho')
    if len(out)!=size: raise ValueError('Tamanho RefPack não confere')
    return bytes(out)


def unpack(src):
    if src[:7]==b'GD.STRM': return src
    if src[:2]==b'\x10\xfb': return refpack(src)
    if src[:8] not in [b'chunkzip',b'chunkref']: raise ValueError('Contêiner desconhecido')
    version,size,width,count,alignment=struct.unpack_from('>5I',src,8)
    if version!=2 or not 0<size<=LIMIT or not width or count!=(size+width-1)//width:
        raise ValueError('Cabeçalho chunk inválido')
    p=32;out=bytearray()
    for i in range(count):
        if src[:8]==b'chunkref':
            p=(p+7)&~7
            if p&15!=8:p+=8
        else:
            p=(p+3)&~3
            while src[p:p+4]==b'\0'*4:p+=4
        stored,flag=struct.unpack_from('>II',src,p);p+=8
        if stored<=0 or p+stored>len(src): raise ValueError('Bloco truncado')
        block=src[p:p+stored];p+=stored
        if flag==1:block=zlib.decompress(block,-15)
        elif flag==2:block=refpack(block)
        elif flag!=4:raise ValueError('Codec de bloco desconhecido')
        if len(block)!=min(width,size-len(out)): raise ValueError('Bloco com tamanho errado')
        out.extend(block)
    if len(out)!=size:raise ValueError('Tamanho do banco não confere')
    return bytes(out)


def big_entries(path):
    with path.open('rb') as handle:
        header=handle.read(16)
        if header[:4] not in [b'BIG4',b'BIGF']:return []
        count,size=struct.unpack_from('>II',header,8)
        if count>200000 or not 16<=size<=32*1024*1024: raise ValueError('Índice BIG inválido')
        handle.seek(0);data=handle.read(size)
    rows=[];p=16
    for i in range(count):
        offset,length=struct.unpack_from('>II',data,p);p+=8;end=data.index(0,p)
        name=data[p:end].decode('utf8');p=end+1
        rows.append((name,offset,length))
    return rows
