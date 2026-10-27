"""Execute the actual generated APT with the existing offline AVM test harness."""
from formats import AptFile,BigFile,Placement
from apt_actions import Actions
from apt_vm import Object,Native
from apt_test_vm import NativeVM
from native_screen import FULL

class MarketVM(NativeVM):
    def invoke(self,function,owner,args=()):
        if self.depth==0:self.steps=0
        return super().invoke(function,owner,args)

def open_native(path,full=FULL,setup=None,callbacks=None):
    apt=AptFile(BigFile(path));actions=Actions(apt).read_all();assert not actions.errors
    calls=[]
    def native(name,obj,args):
        calls.append((name,args))
        if callbacks and name in callbacks:return callbacks[name](obj,args)
        if name in ('Create','CreateHelpTickerItem'):return tuple(args)
        if name=='GetScreenStaticData':return Object({'SCREEN_CONTROLLER_ID':'Calendar'})
        if name=='GetEvents':return Object({'BACK':'Back'})
    vm=MarketVM(native)
    manager={k:Object({n:Native(n) for n in methods}) for k,methods in {
        'InputManager':('SetLocalEventHandler','DisableCurrentLocalEventHandler'),
        'ScreenManager':('SetOnExitScreenCallback','BeginAnimateIn'),
        'HelpManager':('Update','Clear')}.items()}
    manager['InputCodes']=Object(dict(BACK=1,ADVANCE=2,PRIMARY_SELECT=7,LEFT=5,RIGHT=6,UP=3,DOWN=4,L1=8,R1=9,OPTION_TOP=10,L2=11,R2=12,LAS_LEFT=13,LAS_RIGHT=14,LAS_UP=15,LAS_DOWN=16))
    vm.global_.set('game',Object({'globalClasses':Object(manager)}))
    vm.global_.set('ION_CareerMode',Object({n:Native(n) for n in ('GetScreenStaticData','GetEvents','SendEvent','SendSystemEvent')}))
    vm.global_.set('cafe',Object({'utility':Object({'Delegate':Object({'Create':Native('Create')})})}))
    vm.global_.set('ion',Object({'screen':Object({'BaseScreen':Object({'prototype':Object({'Initialize':Native('Initialize'),'Shutdown':Native('Shutdown')})})}),'manager':Object({'HelpItem':Object({'CreateHelpTickerItem':Native('CreateHelpTickerItem')})})}))
    if setup:setup(vm,calls)
    blocks=list(actions.cache.values());vm.pending_packages={full:blocks[0]};vm.run(blocks[1],vm.global_,vm.global_)
    klass=vm.path(full)
    def children(cid):
        char=apt.characters.get(cid)
        if char is None or char.type!=5:return Object()
        return Object({p.name:children(p.character) for p in char.frames[0] if isinstance(p,Placement) and p.name})
    screen=Object({p.name:children(p.character) for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name},klass.get('prototype'))
    vm.invoke(klass,screen)
    return vm,screen,apt,calls
