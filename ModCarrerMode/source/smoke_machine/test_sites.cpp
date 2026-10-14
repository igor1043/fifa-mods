#include "launch_sites.h"
#include "presentation.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
int main(){
    static_assert(machineCount==20,"All opening and goal emitters need a physical base");
    for(size_t i=0;i<machineCount;++i){
        const auto& s=machineSites[i];assert(std::isfinite(s.x)&&std::isfinite(s.z)&&std::isfinite(s.yaw));
        // All hardware stays outside a 105m x 68m playable rectangle.
        assert(std::fabs(s.x)>5250 || std::fabs(s.z)>3400);
        assert(s.x!=0);
        for(size_t j=0;j<i;++j)assert(s.x!=machineSites[j].x||s.z!=machineSites[j].z);
    }
    for(bool retained:{false,true}){
        const auto page=pyro_page("game/screens/playNow/KickOffHub",true,retained);
        assert(page==PyroPage::Outside && !pyro_can_continue(page,true,retained));
    }
    assert(!pyro_can_continue(pyro_page("",false),true,true));
    assert(pyro_can_continue(pyro_page("",true),true,true));
    assert(!pyro_can_continue(pyro_page("",true),false,true));
    assert(pyro_can_continue(pyro_page("game/screens/fluxHub/FluxHub",true),true,true));
    std::puts("20 distinct sites outside pitch; no machine on midfield; preview blocked; native fixture required: PASS");
}
