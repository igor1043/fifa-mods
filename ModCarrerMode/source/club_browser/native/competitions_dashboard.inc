 // The APT owns entry/Back and modal transitions. Native edges own scrolling,
 // focus and tab changes; dispatching both would advance twice on a controller.
 void dashboardControls(HWND window,float w,float h){
  DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);if(pid!=GetCurrentProcessId()){controlReady=false;return;}
  bool held[256]{},edge[256]{};for(int i=0;i<256;++i){held[i]=(GetAsyncKeyState(i)&0x8000)!=0;edge[i]=controlReady&&held[i]&&!keyState[i];keyState[i]=held[i];}
  XINPUT_STATE pad{};if(readPad)for(DWORD i=0;i<4;++i)if(readPad(i,&pad)==ERROR_SUCCESS)break;
  WORD buttons=pad.Gamepad.wButtons,edges=controlReady?buttons&~previousPad:0;previousPad=buttons;
  bool lt=pad.Gamepad.bLeftTrigger>120,rt=pad.Gamepad.bRightTrigger>120,leftTrigger=controlReady&&lt&&!leftTriggerHeld,rightTrigger=controlReady&&rt&&!rightTriggerHeld;leftTriggerHeld=lt;rightTriggerHeld=rt;
  if(!controlReady){controlReady=true;repeatDirection=detailDirection=0;wheelDelta.exchange(0);return;}if(!ready||data.competitions.empty())return;
  auto&c=data.competitions[selected];auto now=GetTickCount64();POINT p{};GetCursorPos(&p);ScreenToClient(window,&p);float fit=(std::min)(w/1600,h/900);if(fit<=0)return;float mx=(p.x-(w-1600*fit)/2)/fit,my=(p.y-(h-900*fit)/2)/fit;
  if(edge[VK_LBUTTON]&&my>=25&&my<105&&mx>=1470&&(expanded||nav.rounds||nav.fullList>=0)){command("comp_close");return;}
  if(expanded&&nav.fullList<0){bracketControls(window,w,h,edge,edges,pad.Gamepad);return;}
  int direction=(held[VK_LEFT]||(buttons&XINPUT_GAMEPAD_DPAD_LEFT)||pad.Gamepad.sThumbLX< -16000)?1:(held[VK_RIGHT]||(buttons&XINPUT_GAMEPAD_DPAD_RIGHT)||pad.Gamepad.sThumbLX>16000)?2:(held[VK_UP]||(buttons&XINPUT_GAMEPAD_DPAD_UP)||pad.Gamepad.sThumbLY>16000)?3:(held[VK_DOWN]||(buttons&XINPUT_GAMEPAD_DPAD_DOWN)||pad.Gamepad.sThumbLY< -16000)?4:0;
  bool step=direction&&(direction!=repeatDirection||now>=repeatAt);if(step)repeatAt=now+(direction!=repeatDirection?340:125);repeatDirection=direction;
  int phaseAxis=pad.Gamepad.sThumbRX>14000?1:pad.Gamepad.sThumbRX< -14000?-1:0;int rs=pad.Gamepad.sThumbRY>14000?-1:pad.Gamepad.sThumbRY< -14000?1:0;
  bool rstep=rs&&(rs!=detailDirection||now>=detailAt);if(rstep)detailAt=now+(rs!=detailDirection?300:(nav.focus==1||nav.focus==2)&&!nav.rounds&&nav.fullList<0?280:85);detailDirection=rs;
  int wheel=wheelDelta.exchange(0);
  if(nav.fullList>=0){
   if(edge['X']||edge['C']||(edges&(XINPUT_GAMEPAD_LEFT_SHOULDER|XINPUT_GAMEPAD_RIGHT_SHOULDER)))nav.openList(1-nav.fullList);
   if(leftTrigger)nav.openList(0);if(rightTrigger)nav.openList(1);
   if(step){if(direction<3)nav.openList(direction==1?0:1);else nav.scroll(direction==3?-1:1,0,scroll,c);}if(rstep)nav.scroll(rs,0,scroll,c);if(edge[VK_PRIOR])nav.scroll(-12,0,scroll,c);if(edge[VK_NEXT])nav.scroll(12,0,scroll,c);if(wheel)nav.scroll(wheel>0?-3:3,0,scroll,c);
   if(edge[VK_LBUTTON]){if(my>=110&&my<150&&mx>=250&&mx<1350)nav.openList(mx<800?0:1);else if(my>=203&&my<720)nav.listSelected=std::clamp(nav.listScroll+int((my-203)/43),0,(std::max)(0,int(c.leaders[nav.fullList].size())-1));}return;
  }
  if(nav.rounds){
   if(leftTrigger||edge['W']||edge['X']||(edges&XINPUT_GAMEPAD_LEFT_SHOULDER))nav.stepRound(-1,c);if(rightTrigger||edge['E']||edge['C']||(edges&XINPUT_GAMEPAD_RIGHT_SHOULDER))nav.stepRound(1,c);
   if(step){if(direction<3)nav.stepRound(direction==1?-1:1,c);else nav.scroll(direction==3?-1:1,0,scroll,c);}if(rstep)nav.scroll(rs,0,scroll,c);if(wheel)nav.scroll(wheel>0?-1:1,0,scroll,c);
   if(edge[VK_LBUTTON]&&my>=115&&my<165){if(mx>=100&&mx<250)nav.stepRound(-1,c);else if(mx>=1350&&mx<1500)nav.stepRound(1,c);}return;
  }
  if(edge['X']||(edges&XINPUT_GAMEPAD_LEFT_SHOULDER)){command("comp_prev");return;}if(edge['C']||(edges&XINPUT_GAMEPAD_RIGHT_SHOULDER)){command("comp_next");return;}
  if(edge['R']||(edges&XINPUT_GAMEPAD_X)){command("comp_rounds");return;}if(edge['M']||(edges&XINPUT_GAMEPAD_Y))command("comp_mode");
  if(edge[VK_TAB])nav.moveFocus(held[VK_SHIFT]?-1:1);if(leftTrigger||edge['W'])nav.moveFocus(-1);if(rightTrigger||edge['E'])nav.moveFocus(1);
  if(step){if(held[VK_SHIFT]&&direction>=3&&nav.focus==0)command(direction==3?"comp_up":"comp_down");else nav.moveSpatial(direction==1?-1:direction==2?1:0,direction==3?-1:direction==4?1:0);}
  if(edge[VK_HOME])command("comp_left");if(edge[VK_END])command("comp_right");
  if(rstep||edge[VK_PRIOR]||edge[VK_NEXT])nav.scrollPage((edge[VK_PRIOR]?-1:edge[VK_NEXT]?1:rs)*(edge[VK_PRIOR]||edge[VK_NEXT]?400:38));
  // Horizontal right stick pages the focused ranking; vertical always scrolls
  // the complete dashboard, regardless of which of its six cards has focus.
  static int priorPhase=0;static uint64_t phaseAt=0;if(phaseAxis&&(phaseAxis!=priorPhase||now>=phaseAt)){if(nav.focus==1||nav.focus==2)nav.pageLeader(nav.focus-1,phaseAxis,c);else if(nav.focus==0&&c.format=="cup")command(phaseAxis<0?"comp_left":"comp_right");phaseAt=now+(phaseAxis!=priorPhase?330:280);}priorPhase=phaseAxis;
  float contentY=my+nav.detail;
  if(edge[VK_LBUTTON]){
   if(my>=20&&my<100){if(mx<130)command("comp_prev");else if(mx>1470)command("comp_next");}
   else if(my>=100&&my<142&&mx>=48&&mx<1552){int n=int(data.competitions.size());selected=std::clamp(int((mx-48)/(1504.f/n)),0,n-1);resetSelection();}
   else if(my>=155&&my<790){if(clubcomp::tableArea.contains(mx,contentY))nav.focus=0;else if(clubcomp::goalsArea.contains(mx,contentY))nav.focus=1;else if(clubcomp::assistsArea.contains(mx,contentY))nav.focus=2;else if(clubcomp::pitchArea.contains(mx,contentY))nav.focus=3;else if(clubcomp::playerMonthArea.contains(mx,contentY))nav.focus=4;else if(clubcomp::coachMonthArea.contains(mx,contentY))nav.focus=5;
    if(c.format=="cup"&&c.groups.empty()&&contentY>=165&&contentY<200){if(mx>=69&&mx<99)command("comp_left");else if(mx>=695&&mx<725)command("comp_right");}
    bool paged=false;for(int k=0;k<2;++k){auto box=k?clubcomp::assistsArea:clubcomp::goalsArea;if(contentY>=box.y+275&&contentY<box.y+306){if(mx>=box.x+10&&mx<box.x+52){nav.pageLeader(k,-1,c);paged=true;}else if(mx>=box.x+box.w-52&&mx<box.x+box.w-10){nav.pageLeader(k,1,c);paged=true;}}}
    if(!paged&&(nav.focus==1||nav.focus==2))command(nav.focus==1?"comp_goals":"comp_assists");else if(nav.focus==0&&clubcomp::roundsButton.contains(mx,contentY))command("comp_rounds");
   }
  }
  if(held[VK_LBUTTON]&&mx>=1545&&mx<1558&&my>=166&&my<=779){float track=603,thumb=track*clubcomp::detailViewportHeight/clubcomp::detailContentHeight;nav.detail=int(std::clamp((my-171-thumb/2)/(track-thumb),0.f,1.f)*clubcomp::detailMaximumScroll);}
  if(wheel&&mx>=60&&mx<1558&&my>=155&&my<790){nav.scrollPage(wheel>0?-82:82);}
 }
 void leaderCards(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;for(int kind=0;kind<2;++kind){const auto box=kind?clubcomp::assistsArea:clubcomp::goalsArea;panel(c,box.x,box.y,box.w,box.h);
   text(c,kind?"ASSISTÊNCIAS":"ARTILHEIROS",box.x+17,box.y+11,220,30,22);text(c,"Ver todos ›",box.x+box.w-112,box.y+15,98,23,14,uitheme::accentInk(),true);r.line(c,box.x+12,box.y+49,box.x+box.w-12,box.y+49,0xffe5edf3);
   auto&list=comp.leaders[kind];int pages=nav.pages(kind,comp);nav.leaders[kind]=std::clamp(nav.leaders[kind],0,(std::max)(0,pages-1));int start=nav.leaders[kind]*3;
   for(int i=0;i<3&&start+i<int(list.size());++i){auto&p=list[start+i];int rank=start+i+1;float y=box.y+59+i*70.f,x=box.x;
    rounded(c,x+10,y,box.w-20,64,7,clubcomp::medalColor(rank));rounded(c,x+17,y+19,24,27,4,0xaaffffff);
    unsigned tone=clubcomp::medalInk(rank);COLORREF medal=RGB((tone>>16)&255,(tone>>8)&255,tone&255);text(c,std::to_string(rank),x+17,y+19,24,27,18,medal,true);
    image(c,"head",p.id,x+46,y+2,49,60);image(c,"crest",p.club,x+79,y+41,20,21);
    text(c,p.name,x+108,y+5,180,24,18);text(c,p.position,x+108,y+28,180,18,12,RGB(100,125,148));text(c,p.clubName,x+108,y+45,180,17,12,RGB(100,125,148));text(c,std::to_string(p.value),x+box.w-51,y+15,37,35,27,medal,true);
   }
   if(list.empty())text(c,"Sem registros nesta competição",box.x+20,box.y+135,int(box.w)-40,55,18,RGB(116,138,150),true);
   text(c,"‹",box.x+13,box.y+276,32,27,25,uitheme::accentInk(),true);text(c,"›",box.x+box.w-45,box.y+276,32,27,25,uitheme::accentInk(),true);
   for(int page=0;page<pages;++page)rounded(c,box.x+box.w/2-pages*10+page*20.f,box.y+282,13,5,2.5f,page==nav.leaders[kind]?uitheme::accent():0xffcddce7);
   text(c,list.empty()?"Aguardando partidas":std::to_string(start+1)+"–"+std::to_string((std::min)(start+3,(std::min)(9,int(list.size()))))+" de "+std::to_string((std::min)(9,int(list.size()))),box.x+53,box.y+292,int(box.w)-106,15,11,RGB(109,132,152),true);
  }
 }
 void coachPortrait(ID3D11DeviceContext*c,const std::string&name,float x,float y,float w,float h){
  if(name.empty())return;auto&t=images["coach:"+name];clubgfx::gameImage(renderer.device,t,art,{"ModCarrerMode/data/manager_market/"+name});if(!t.view||!t.w||!t.h)return;float fit=(std::min)(w/t.w,h/t.h);renderer.normal(c);renderer.quad(c,x+(w-t.w*fit)/2,y+(h-t.h*fit)/2,t.w*fit,t.h*fit,t.view);
 }
 void monthlyCard(ID3D11DeviceContext*c,const clubcomp::MonthlyAward&a,bool coach,float x,float y,float w){
  panel(c,x,y,w,216);text(c,coach?"TÉCNICO DO MÊS":"JOGADOR DO MÊS",x+16,y+12,int(w)-32,29,22);
  const char*months[]={"","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"};int month=a.month%100;std::string stamp=month>0&&month<13?std::string(months[month])+" · "+std::to_string(a.month/100):"Mês atual";
  text(c,stamp+" · prévia",x+16,y+45,int(w)-32,24,14,uitheme::accentInk());renderer.line(c,x+16,y+77,x+w-26,y+77,0xffe5edf3);
  if(a.available){rounded(c,x+16,y+91,73,95,7,0xffedf3f7);if(coach)coachPortrait(c,a.image,x+17,y+91,71,94);else image(c,"head",a.id,x+17,y+91,71,94);
   text(c,a.name,x+103,y+88,int(w)-134,28,21);image(c,"crest",a.club,x+103,y+121,23,24);text(c,a.clubName,x+135,y+121,int(w)-164,25,16,RGB(100,125,148));text(c,a.metric,x+103,y+155,int(w)-134,26,18,uitheme::accentInk());text(c,a.note,x+16,y+190,int(w)-32,20,12,RGB(109,132,152));
  }else{text(c,"Histórico mensal em formação",x+18,y+102,int(w)-36,33,20,RGB(100,125,148));text(c,a.note.empty()?"Os destaques aparecerão após novas partidas.":a.note,x+18,y+145,int(w)-36,50,15,RGB(109,132,152));}
 }
 void dashboardBody(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;if(!canvasClip){D3D11_RASTERIZER_DESC desc{};r.raster->GetDesc(&desc);desc.ScissorEnable=TRUE;r.device->CreateRasterizerState(&desc,&canvasClip);}
  D3D11_RECT old[16]{};UINT count=16;c->RSGetScissorRects(&count,old);D3D11_RECT clip{LONG(r.left+60*r.scale),LONG(r.top+155*r.scale),LONG(r.left+1541*r.scale),LONG(r.top+790*r.scale)};
  auto apply=[&](){if(canvasClip){c->RSSetState(canvasClip);c->RSSetScissorRects(1,&clip);}};
  float oldTop=r.top;r.top-=nav.detail*r.scale;apply();
  if(comp.format=="cup"&&!comp.groups.empty())mixed(c,comp);else if(comp.format=="cup")cup(c,comp);else table(c,comp);
  apply();leaderCards(c,comp);pitch(c,comp);monthlyCard(c,comp.awards[0],false,60,810,732);monthlyCard(c,comp.awards[1],true,808,810,732);
  const clubcomp::Area areas[]={clubcomp::tableArea,clubcomp::goalsArea,clubcomp::assistsArea,clubcomp::pitchArea,clubcomp::playerMonthArea,clubcomp::coachMonthArea};auto box=areas[std::clamp(nav.focus,0,5)];
  unsigned focus=uitheme::accent();r.line(c,box.x+2,box.y+2,box.x+box.w-2,box.y+2,focus);r.line(c,box.x+2,box.y+2,box.x+2,box.y+box.h-2,focus);r.line(c,box.x+box.w-2,box.y+2,box.x+box.w-2,box.y+box.h-2,focus);r.line(c,box.x+2,box.y+box.h-2,box.x+box.w-2,box.y+box.h-2,focus);
  r.top=oldTop;c->RSSetState(r.raster);c->RSSetScissorRects(count,old);
  float track=603,thumb=track*clubcomp::detailViewportHeight/clubcomp::detailContentHeight;rounded(c,1548,171,5,track,2.5f,0xffdce6ee);rounded(c,1548,171+(track-thumb)*nav.detail/clubcomp::detailMaximumScroll,5,thumb,2.5f,uitheme::accent());
 }
 void drawMatchdays(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;r.rectangle(c,40,20,1520,790,0xfff8fbfe);image(c,"comp",comp.asset,81,45,56,54);text(c,"RESULTADOS POR RODADA",154,42,1180,36,29);text(c,comp.name,155,82,1160,25,17,RGB(109,132,152));text(c,"×",1470,39,65,44,31,uitheme::accentInk(),true);
  if(comp.matchdays.empty()){text(c,"Nenhuma rodada identificada na carreira",160,342,1280,60,27,RGB(100,125,148),true);text(c,"Os jogos aparecerão quando a competição publicar suas rodadas.",160,406,1280,50,20,RGB(109,132,152),true);return;}
  nav.matchday=std::clamp(nav.matchday,0,int(comp.matchdays.size())-1);auto&day=comp.matchdays[nav.matchday];text(c,"L2  ‹  Anterior",100,118,155,35,20,uitheme::accentInk(),true);text(c,"Próxima  ›  R2",1345,118,155,35,20,uitheme::accentInk(),true);
  text(c,day.name+(day.played<int(day.matches.size())?"  ·  "+std::to_string(day.played)+" / "+std::to_string(day.matches.size())+" concluídos":""),250,116,1100,36,23,RGB(25,52,76),true);r.line(c,86,168,1512,168,0xffdce6ee);
  nav.matchScroll=std::clamp(nav.matchScroll,0,(std::max)(0,int(day.matches.size())-12));int visible=(std::min)(12,int(day.matches.size())-nav.matchScroll);float rowHeight=(std::min)(66.f,532.f/(std::max)(1,(std::min)(12,int(day.matches.size()))));
  for(int i=0;i<visible;++i){auto&m=day.matches[nav.matchScroll+i];float y=186+i*rowHeight;bool own=m.home==data.club||m.away==data.club;rounded(c,85,y,1414,rowHeight-5,7,own?0xfffff2d5:i%2?0xffedf3f8:0xfff5f8fb);
   auto date=std::to_string(m.date);date=date.size()==8?date.substr(6,2)+"/"+date.substr(4,2)+"/"+date.substr(0,4):"A definir";text(c,date,103,y+4,180,22,16);text(c,m.time,103,y+24,180,18,12,RGB(109,132,152));
   image(c,"crest",m.home,348,y+6,34,34);text(c,m.homeName,403,y+8,300,31,21);image(c,"crest",m.away,1385,y+6,34,34);text(c,m.awayName,1013,y+8,360,31,21);
   text(c,m.played?std::to_string(m.h)+"  –  "+std::to_string(m.a):"×",752,y+5,207,31,m.played?25:22,uitheme::accentInk(),true);if(!m.played)text(c,"Agendado",752,y+29,207,17,11,RGB(109,132,152),true);
  }
  text(c,std::to_string(nav.matchScroll+1)+"–"+std::to_string(nav.matchScroll+visible)+" de "+std::to_string(day.matches.size())+" jogos  ·  "+std::to_string(nav.matchday+1)+" / "+std::to_string(comp.matchdays.size())+" rodadas",130,743,1340,26,16,RGB(109,132,152),true);
  if(day.matches.size()>12){float track=518,thumb=track*12/day.matches.size();rounded(c,1515,187,5,track,2,0xffdce6ee);rounded(c,1515,187+(track-thumb)*nav.matchScroll/(day.matches.size()-12),5,thumb,2,uitheme::accent());}
 }

 void drawFullLeaders(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;r.rectangle(c,40,20,1520,790,0xfff8fbfe);int kind=std::clamp(nav.fullList,0,1);auto&list=comp.leaders[kind];image(c,"comp",comp.asset,80,36,58,57);text(c,kind?"ASSISTÊNCIAS":"ARTILHEIROS",156,35,1140,40,31);text(c,comp.name,158,78,1130,25,17,RGB(109,132,152));text(c,"×",1470,39,65,44,31,uitheme::accentInk(),true);
  for(int k=0;k<2;++k){float x=250+k*550.f;rounded(c,x,113,546,35,6,k==kind?uitheme::accent():0xffe9f0f5);text(c,k?"Assistências":"Artilheiros",x+8,115,530,31,19,k==kind?uitheme::selectedText():RGB(29,54,77),true);}
  const char*headers[]={"#","JOGADOR","CLUBE","POSIÇÃO","JOGOS",kind?"ASSISTÊNCIAS":"GOLS"};const int xx[]={86,185,635,900,1190,1355},ww[]={45,380,240,240,100,150};for(int i=0;i<6;++i)text(c,headers[i],float(xx[i]),166,ww[i],27,14,RGB(109,132,152),i==0||i>=4);
  nav.listSelected=std::clamp(nav.listSelected,0,(std::max)(0,int(list.size())-1));nav.listScroll=std::clamp(nav.listScroll,0,(std::max)(0,int(list.size())-12));int visible=(std::min)(12,int(list.size())-nav.listScroll);
  for(int i=0;i<visible;++i){int index=nav.listScroll+i;auto&p=list[index];float y=203+i*43.f;rounded(c,78,y,1428,39,5,index==nav.listSelected?0xfffff0cb:i%2?0xffedf3f8:0xfff5f8fb);rounded(c,88,y+6,30,27,4,clubcomp::medalColor(index+1));unsigned tone=clubcomp::medalInk(index+1);text(c,std::to_string(index+1),88,y+6,30,27,18,RGB((tone>>16)&255,(tone>>8)&255,tone&255),true);image(c,"head",p.id,130,y+1,39,38);text(c,p.name,185,y+5,380,30,21);image(c,"crest",p.club,592,y+6,28,28);text(c,p.clubName,635,y+5,240,30,19);text(c,p.position,900,y+5,240,30,18,RGB(109,132,152));text(c,std::to_string(p.games),1190,y+5,100,30,20,RGB(29,54,77),true);text(c,std::to_string(p.value),1355,y+5,150,30,24,uitheme::accentInk(),true);}
  if(list.empty())text(c,"Nenhum registro nesta competição",120,365,1360,60,26,RGB(109,132,152),true);
  text(c,list.empty()?"":std::to_string(nav.listScroll+1)+"–"+std::to_string(nav.listScroll+visible)+" de "+std::to_string(list.size()),1150,741,350,26,16,RGB(109,132,152),true);text(c,"L1 / R1  ·  Ranking     Analógico / roda do mouse  ·  Rolar lista",90,776,1300,24,15,RGB(109,132,152));
  if(list.size()>12){float track=510,thumb=track*12/list.size();rounded(c,1521,204,5,track,2,0xffdce6ee);rounded(c,1521,204+(track-thumb)*nav.listScroll/(list.size()-12),5,thumb,2,uitheme::accent());}
 }
