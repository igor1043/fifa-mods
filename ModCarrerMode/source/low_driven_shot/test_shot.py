"""Differential check against the supplied mod's pure exported state machine."""
import ctypes as c
import random
from pathlib import Path
import sys

class Pad(c.Structure):
    _fields_=[('buttons',c.c_uint16),('lt',c.c_uint8),('rt',c.c_uint8),('lx',c.c_int16),('ly',c.c_int16),('rx',c.c_int16),('ry',c.c_int16)]
class Input(c.Structure):
    _fields_=[('packet',c.c_uint32),('pad',Pad)]
class State(c.Structure):
    _fields_=[('phase',c.c_int),('reserved',c.c_int),('started',c.c_uint64),('packet',c.c_uint32),('last',Pad),('prev',c.c_int),('prevLt',c.c_int),('pressed',c.c_uint64),('released',c.c_uint64),('outPressed',c.c_uint64),('charge',c.c_uint64)]

def run(original):
    old=c.WinDLL(str(original)).ChuteRasteiroProcessar
    new=c.WinDLL(str(Path(__file__).parent/'build/low_driven_shot.dll')).Fifa16LowDrivenShotProcess
    args=[c.POINTER(State),c.POINTER(Input),c.POINTER(Input),c.c_uint64,c.c_int,c.c_int,c.c_int,c.c_uint16,c.c_int,c.c_int]
    for f in old,new:f.argtypes=args;f.restype=None
    rng=random.Random(16);samples=0
    for mode in range(3):
        for trial in range(150):
            a,b=State(),State();now=1000;pad=Pad();button=rng.choice([0x2000,0x4000]);height=rng.randrange(101);tap=rng.randrange(60,1001)
            for frame in range(800):
                now+=rng.choice([1,4,8,16,33,60,100])
                if rng.random()<.12:pad.buttons^=button
                if rng.random()<.02:pad.buttons^=0x200
                if rng.random()<.03:pad.lt=rng.choice([0,30,31,255])
                if rng.random()<.03:pad.rt=rng.choice([0,30,31,255])
                pad.lx=rng.randrange(-32768,32768)
                inp=Input(frame,pad);oa,ob=Input(),Input()
                old(c.byref(a),c.byref(inp),c.byref(oa),now,1,height,30,button,mode,tap)
                new(c.byref(b),c.byref(inp),c.byref(ob),now,1,height,30,button,mode,tap)
                assert bytes(oa)==bytes(ob) and bytes(a)==bytes(b),(mode,trial,frame,now,a.phase,b.phase,bytes(a).hex(),bytes(b).hex())
                samples+=1
    print(f'PASS: {samples} controller samples match the supplied mod; all three modes, timings, triggers and both shoot buttons.')
if __name__=='__main__':run(Path(sys.argv[1]))
