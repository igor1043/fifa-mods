"""Offline branch audit; never writes the game or starts a process."""
from pathlib import Path
import argparse,json,re,struct
import pefile
ROOT=Path(__file__).parent
SITES=((0x4a88aa7,0xe9,0x5bea150),(0x5950c5a,0xe8,0x5bea150),(0x4907538,0xe8,0x4908c70),(0x48fd7fb,0xe8,0x48ec5e0))
def verify(path):
    pe=pefile.PE(str(path),fast_load=True)
    assert pe.FILE_HEADER.Machine==0x8664 and pe.FILE_HEADER.TimeDateStamp==0x577de45c
    source=(ROOT/'native_sites.h').read_text()
    signatures=[bytes.fromhex(s.replace('0x','').replace(',',' ')) for s in re.findall(r'\{0x[0-9a-f]+,\{([^}]+)\}\}',source)]
    assert len(signatures)==len(SITES)
    rows=[]
    for (rva,opcode,target),expected in zip(SITES,signatures):
        data=pe.get_data(rva,16)
        assert data==expected,(hex(rva),data.hex(),expected.hex())
        assert data[0]==opcode and rva+5+struct.unpack_from('<i',data,1)[0]==target
        rows.append(dict(rva=hex(rva),target=hex(target),bytes=data.hex()))
    # FIFO handler copies exactly 0xb0 bytes and schedules native overlay 75.
    assert pe.get_data(0x48ec6cc,8)==bytes.fromhex('c74424204b000000')
    assert pe.get_data(0x48ec6d7,8)==bytes.fromhex('c74424240a000000')
    # Native title branch and home/away field reads used by the adapter.
    assert pe.get_data(0x48e8c8f,7)==bytes.fromhex('83bb887f000001')
    return rows
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('binary',type=Path);args=parser.parse_args()
    print(json.dumps(dict(verified=True,sites=verify(args.binary)),indent=2))
