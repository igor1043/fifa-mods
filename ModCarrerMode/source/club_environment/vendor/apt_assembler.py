import struct
class Assembler:
    def __init__(self, data):
        self.data, self.fixups, self.labels = data, [], {}
        self.parameters = []

    def align(self): self.data.extend(bytes(-len(self.data) % 8))
    def op(self, value): self.data.append(value)
    def reg(self, n): self.data.extend((185, n))
    def string(self, value):
        self.op(161); self.align()
        at = len(self.data); self.data.extend(bytes(8))
        self.fixups.append((at, value))

    def member(self, name): self.string(name); self.op(78)
    def method(self, name): self.string(name); self.op(82)
    def path(self, *parts):
        self.string(parts[0]); self.op(28)
        for part in parts[1:]: self.member(part)

    def global_object(self):
        # FIFA's 0x58 pushes the STRING "_global"; 0x71 pushes its object.
        # SetMember on 0x58 cannot persist the hub owner between widgets.
        self.op(113)

    def branch(self, label, conditional=True):
        self.op(157 if conditional else 153); self.align()
        at = len(self.data); self.data.extend(bytes(4))
        self.fixups.append((at, ('branch', label)))

    def label(self, label): self.labels[label] = len(self.data)
    def store(self, register):
        self.op(135); self.align(); self.data.extend(struct.pack('<i', register)); self.op(23)

    def property(self, register, name, value):
        self.reg(register); self.string(name); self.op(115 if value else 116); self.op(79)

    def original(self, name, count=0):
        for register in reversed(range(2, count + 2)): self.reg(register)
        self.op(181); self.op(count); self.reg(1); self.method('Server16Original' + name)

    def finish(self):
        for pointer, count in self.parameters:
            self.align(); struct.pack_into('<Q', self.data, pointer, len(self.data))
            if not count: self.data.extend(bytes(16))
            for index in range(count):
                self.align(); self.data.extend(struct.pack('<I', index + 2)); self.align()
                at = len(self.data); self.data.extend(bytes(8)); self.fixups.append((at, 'argument' + str(index)))
        strings = {}
        for at, value in self.fixups:
            if isinstance(value, tuple):
                struct.pack_into('<i', self.data, at, self.labels[value[1]] - at - 4)
            else:
                if value not in strings:
                    strings[value] = len(self.data); self.data.extend(value.encode('ascii') + b'\0')
                struct.pack_into('<Q', self.data, at, strings[value])
