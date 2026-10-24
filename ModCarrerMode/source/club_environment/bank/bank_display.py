"""Native APT display depths are unique slots, not painter-order hints."""
import struct

def normalize_root(data,controls,fields,buttons):
    fields={row[0] for row in fields};buttons={row[0] for row in buttons}
    counters={}
    names=set()
    for pointer in controls:
        flags=struct.unpack_from('<i',data,pointer+8)[0]
        text=struct.unpack_from('<Q',data,pointer+56)[0] if flags&32 else 0
        name=bytes(data[text:data.index(0,text)]).decode('utf8') if text else ''
        if name:
            if name in names:raise ValueError('Instância APT duplicada: '+name)
            names.add(name)
        if name in fields:band=1000
        elif name.startswith(('bankLogo','bankHeaderLogo')):band=4000
        elif name.startswith('tableRow'):band=100
        elif name in buttons:band=2000
        else:band=100
        counters[band]=counters.get(band,0)+1
        struct.pack_into('<i',data,pointer+12,band+counters[band])
