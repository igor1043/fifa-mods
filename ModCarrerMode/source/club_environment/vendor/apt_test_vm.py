import copy
from apt_vm import VM
class NativeVM(VM):
    def path(self,name,scope=None):
        # Native unplaced __Packages symbols initialize only on a full-name
        # variable lookup, not on successive namespace member reads.
        pending=getattr(self,'pending_packages',{})
        if name in pending:
            self.run(pending.pop(name),self.global_,self.global_)
        return super().path(name,scope)

    def run(self,code,*args,**kwargs):
        adjusted=[]
        for instruction in code:
            if instruction.op==88:
                instruction=copy.copy(instruction);instruction.op,instruction.value=161,'_global'
            elif instruction.op==83:
                # The fixture exposes native constructors as factories. Keep
                # opcode 83 in the built APT and invoke that factory in this VM.
                instruction=copy.copy(instruction);instruction.op=82
            adjusted.append(instruction)
        return super().run(adjusted,*args,**kwargs)
