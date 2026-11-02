 void ensureBracket(){auto&c=data.competitions[selected];if(bracketDirty||bracketScene.root!=c.root){bracketScene.build(c);bracketDirty=false;bracketPhase=std::clamp(bracketPhase,0,(std::max)(0,int(c.rounds.size())-1));}}
 void fitBracket(bool snap=false){
  if(data.competitions.empty())return;ensureBracket();auto&c=data.competitions[selected];bracketDrag=false;bracketLast=GetTickCount64();
  if(c.format=="league"){bracketScene.y0=-350;bracketScene.y1=1000;viewport.focus(0,0,1,snap);canvasZoom=1;canvasPanX=canvasPanY=0;return;}
  int last=bracketScene.finalRound>=0?bracketScene.finalRound:(std::max)(0,int(c.rounds.size())-1);bracketPhase=(std::max)(0,last-3);float left=-180,right=180,top=-260,bottom=320;
  for(auto&n:bracketScene.nodes)if(n.round>=bracketPhase&&n.round<=last){left=(std::min)(left,n.x-125);right=(std::max)(right,n.x+125);top=(std::min)(top,n.y-65);bottom=(std::max)(bottom,n.y+65);}
  float z=std::clamp((std::min)(1430/(right-left),490/(bottom-top)),.45f,1.f);viewport.focus((left+right)/2,(top+bottom)/2,z,snap);
 }
 void selectBracketPhase(int index){
  auto&c=data.competitions[selected];if(c.rounds.empty())return;ensureBracket();bracketPhase=(index+int(c.rounds.size()))%int(c.rounds.size());const clubcomp::BracketPosition*chosen=nullptr;bool own=false;
  for(auto&n:bracketScene.nodes)if(n.round==bracketPhase){auto raw=std::find_if(c.nodes.begin(),c.nodes.end(),[&](auto&r){return r.id==n.id;});bool isOwn=raw!=c.nodes.end()&&raw->tie>=0&&(c.rounds[n.round].ties[raw->tie].home==data.club||c.rounds[n.round].ties[raw->tie].away==data.club);
   if(!chosen||(!own&&isOwn)||(!own&&!isOwn&&(n.x<chosen->x||(n.x==chosen->x&&std::abs(n.y)<std::abs(chosen->y))))){chosen=&n;own=isOwn;}
  }
  if(chosen)viewport.focus(chosen->final?0:chosen->x+(chosen->x<0?540.f:-540.f),chosen->final?20.f:chosen->y,chosen->final?.85f:.92f);
 }
 void bracketControls(HWND window,float w,float h,const bool*edge,WORD buttons,const XINPUT_GAMEPAD&p){
  ensureBracket();auto now=GetTickCount64();float dt=bracketLast?(std::min)(.05f,(now-bracketLast)*.001f):1/60.f;bracketLast=now;
  auto key=[](int code){return (GetAsyncKeyState(code)&0x8000)!=0;};
  if(edge['X']||(buttons&XINPUT_GAMEPAD_LEFT_SHOULDER))selectBracketPhase(bracketPhase-1);else if(edge['C']||(buttons&XINPUT_GAMEPAD_RIGHT_SHOULDER))selectBracketPhase(bracketPhase+1);
  int phaseAxis=p.sThumbRX>16000?1:p.sThumbRX< -16000?-1:0;
  if(phaseAxis&&(phaseAxis!=detailDirection||now>=detailAt)){selectBracketPhase(bracketPhase+phaseAxis);detailAt=now+320;}detailDirection=phaseAxis;
  float dx=float(key(VK_RIGHT))-float(key(VK_LEFT))+clubcomp::BracketCamera::axis(p.sThumbLX);
  float dy=float(key(VK_DOWN))-float(key(VK_UP))-clubcomp::BracketCamera::axis(p.sThumbLY);
  dx+=bool(p.wButtons&XINPUT_GAMEPAD_DPAD_RIGHT)-bool(p.wButtons&XINPUT_GAMEPAD_DPAD_LEFT);dy+=bool(p.wButtons&XINPUT_GAMEPAD_DPAD_DOWN)-bool(p.wButtons&XINPUT_GAMEPAD_DPAD_UP);viewport.pan(dx,dy,dt);
  float z=(p.bRightTrigger>32?(p.bRightTrigger-32)/223.f:0)-(p.bLeftTrigger>32?(p.bLeftTrigger-32)/223.f:0)+float(key('E')||key(VK_ADD)||key(VK_OEM_PLUS)||key(VK_PRIOR))-float(key('W')||key(VK_SUBTRACT)||key(VK_OEM_MINUS)||key(VK_NEXT));if(z)viewport.zoomAt(z*dt*1.4f);
  POINT pt{};GetCursorPos(&pt);ScreenToClient(window,&pt);float fit=(std::min)(w/1600,h/900);if(fit<=0)return;float x=(pt.x-(w-1600*fit)/2)/fit,y=(pt.y-(h-900*fit)/2)/fit;
  int wheel=wheelDelta.exchange(0);if(wheel&&y>=150&&y<692){if(key(VK_SHIFT))viewport.drag(0,wheel/float(WHEEL_DELTA)*44);else viewport.zoomAt(wheel/float(WHEEL_DELTA)*.16f,x,y);}
  if(edge[VK_LBUTTON]){
   if(y>=155&&y<691&&x>=55&&x<1545){viewport.targetX=viewport.x;viewport.targetY=viewport.y;viewport.targetZoom=viewport.zoom;bracketDrag=true;bracketMouseX=x;bracketMouseY=y;}
   else if(y>=30&&y<90){if(x>=1190&&x<1245)viewport.zoomAt(-.2f);else if(x>=1250&&x<1305)viewport.zoomAt(.2f);else if(x>=1320&&x<1460)fitBracket();}
   else if(y>=107&&y<145&&!data.competitions[selected].rounds.empty()){int count=int(data.competitions[selected].rounds.size()),visible=(std::min)(8,count),start=std::clamp(bracketPhase-3,0,(std::max)(0,count-visible));if(x>=55&&x<84)selectBracketPhase(bracketPhase-1);else if(x>=1518&&x<1548)selectBracketPhase(bracketPhase+1);else if(x>=86&&x<1514)selectBracketPhase(start+int((x-86)/(1428.f/visible)));}
  }
  if(key(VK_LBUTTON)&&bracketDrag){viewport.drag(x-bracketMouseX,y-bracketMouseY);bracketMouseX=x;bracketMouseY=y;}if(!key(VK_LBUTTON))bracketDrag=false;
  viewport.tick(dt,bracketScene);canvasZoom=viewport.zoom;canvasPanX=-viewport.x*viewport.zoom;canvasPanY=-viewport.y*viewport.zoom;
 }
 static std::string bracketDate(int date){auto s=std::to_string(date);return s.size()==8?s.substr(6,2)+"/"+s.substr(4,2):"A definir";}
 void bracketHighlights(ID3D11DeviceContext*c,const clubcomp::Competition&comp){
  const char*titles[]={"MAIOR GOLEADA","ARTILHEIRO","ASSISTÊNCIAS","MELHOR GOLEIRO","MELHOR DEFESA","MELHOR ATAQUE"};
  for(int k=0;k<6;++k){float x=55+k*250.f,w=240,y=704;panel(c,x,y,w,95);text(c,titles[k],x+13,y+6,218,22,14,RGB(29,54,77));auto&a=comp.insights[k];
   if(!a.available){text(c,"Sem dados registrados",x+13,y+37,214,36,15,RGB(116,138,150),true);continue;}
   if(k==0){image(c,"crest",a.club,x+14,y+32,27,29);image(c,"crest",a.other,x+198,y+32,27,29);text(c,a.value,x+46,y+30,145,31,24,uitheme::accentInk(),true);text(c,a.name+" × "+a.clubName,x+10,y+61,220,17,12,RGB(90,117,141),true);int date=0;try{date=std::stoi(a.detail);}catch(...){}text(c,bracketDate(date),x+10,y+79,220,14,11,RGB(116,138,150),true);}
   else{bool player=k<=3;if(player){image(c,"head",a.id,x+10,y+30,45,56);image(c,"crest",a.club,x+45,y+67,17,18);}else image(c,"crest",a.club,x+12,y+36,42,44);
    text(c,a.name,x+65,y+30,131,24,17);text(c,a.value,x+w-43,y+30,35,30,23,uitheme::accentInk(),true);text(c,player?a.clubName:a.detail,x+65,y+55,164,20,12,RGB(90,117,141));text(c,player?a.detail:k==4?"Gols sofridos · média por jogo":"Gols marcados",x+65,y+76,163,15,11,RGB(116,138,150));}
  }
 }
 void bracketTie(ID3D11DeviceContext*c,const clubcomp::Competition&comp,const clubcomp::BracketPosition&node,const clubcomp::Tie*t){
  auto&r=renderer;float z=viewport.zoom,x=viewport.X(node.x-116),y=viewport.Y(node.y-55),w=232*z,h=110*z;if(x+w<55||x>1545||y+h<181||y>691)return;bool own=t&&(t->home==data.club||t->away==data.club);
  rounded(c,x-1,y-1,w+2,h+2,7*z,own?uitheme::accent():0xffd8e4ed);rounded(c,x,y,w,h,7*z,own?0xfffff8e8:0xfff9fcff);
  auto txt=[&](const std::string&s,float X,float Y,int W,int H,int size,COLORREF ink=RGB(29,54,77),bool center=false){scaledText(c,s,x+X*z,y+Y*z,W,H,size,z,ink,center);};
  if(z>.35f){txt(t&&t->legs.size()>1?"IDA":"",146,1,25,14,10,RGB(116,138,150),true);txt(t&&t->legs.size()>1?"VOLTA":"",170,1,31,14,10,RGB(116,138,150),true);txt("AGG",204,1,26,14,10,uitheme::accentInk(),true);}
  for(int side=0;side<2;++side){float yy=17+side*30.f;int id=t?(side?t->away:t->home):0;image(c,"crest",id,x+8*z,y+yy*z,23*z,24*z);auto ink=t&&id==t->winner?uitheme::accentInk():RGB(29,54,77);txt(t?(side?t->awayName:t->homeName):"A definir",36,yy,108,27,18,ink);
   if(t){if(t->legs.size()>1)for(int leg=0;leg<(std::min)(2,int(t->legs.size()));++leg){auto&m=t->legs[leg];txt(num(m.home==id?m.h:m.a),148+leg*28.f,yy,24,27,18,ink,true);}txt(num(side?t->a:t->h),204,yy,26,27,21,uitheme::accentInk(),true);}
  }
  if(z>.4f){std::string dates=!t||t->legs.empty()?"Sorteio pendente":bracketDate(t->legs[0].date);if(t&&t->legs.size()>1)dates+=" · "+bracketDate(t->legs[1].date);else if(t)dates+=" · jogo único";txt(dates,10,85,212,19,12,RGB(116,138,150),true);}
 }
 void bracketFinal(ID3D11DeviceContext*c,const clubcomp::Competition&comp,const clubcomp::Tie*t){
  auto&r=renderer;float z=viewport.zoom;image(c,"trophy",comp.asset,viewport.X(-122),viewport.Y(-235),244*z,252*z);float x=viewport.X(-165),y=viewport.Y(90),w=330*z;
  rounded(c,x,y,w,220*z,10*z,0xffc9d9e6);rounded(c,x+1,y+1,w-2,220*z-2,9*z,0xfff9fcff);rounded(c,x+29*z,y-19*z,272*z,34*z,7*z,uitheme::accent());
  auto txt=[&](const std::string&s,float X,float Y,int W,int H,int size,COLORREF ink=RGB(29,54,77),bool center=false){scaledText(c,s,x+X*z,y+Y*z,W,H,size,z,ink,center);};
  txt("FINAL",35,-16,260,28,22,uitheme::selectedText(),true);std::string date=!t||t->legs.empty()?"Aguardando definição":bracketDate(t->legs[0].date)+" · "+t->legs[0].time;txt(date,15,25,300,27,17,RGB(99,125,147),true);
  for(int side=0;side<2;++side){int id=t?(side?t->away:t->home):0;image(c,"crest",id,x+(side?244:42)*z,y+64*z,44*z,48*z);txt(t?(side?t->awayName:t->homeName):"A definir",side?193:7,119,130,30,19,RGB(29,54,77),true);}
  txt(t&&t->h>=0?num(t->h)+" – "+num(t->a):"×",122,70,85,40,30,uitheme::accentInk(),true);
  std::string bottom=!t?"Finalistas ainda não registrados":t->legs.size()>1?"Ida "+bracketDate(t->legs[0].date)+" · volta "+bracketDate(t->legs[1].date):"Jogo único";txt(bottom,14,165,302,24,14,RGB(99,125,147),true);
  if(t&&t->legs.size()>1){auto leg=[&](const clubcomp::Leg&m){return num(m.h)+"–"+num(m.a);};txt("Ida "+leg(t->legs[0])+" · volta "+leg(t->legs[1])+" · agregado",14,190,302,20,13,uitheme::accentInk(),true);}
 }
 void drawExpanded(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  ensureBracket();auto&r=renderer;canvasZoom=viewport.zoom;canvasPanX=-viewport.x*viewport.zoom;canvasPanY=-viewport.y*viewport.zoom;
  r.rectangle(c,40,20,1520,790,0xfff1f6fa);r.rectangle(c,40,20,1520,131,0xfff8fbfe);image(c,"comp",comp.asset,78,29,62,64);text(c,comp.name,159,28,1000,43,32);text(c,(comp.format=="league"?"Classificação · ":"Chaveamento · ")+std::to_string(data.date/10000),161,74,1000,26,18,RGB(116,138,150));
  rounded(c,1190,37,55,41,7,0xffedf3f8);rounded(c,1250,37,55,41,7,0xffedf3f8);text(c,"−",1190,38,55,39,30,uitheme::accentInk(),true);text(c,"+",1250,38,55,39,30,uitheme::accentInk(),true);rounded(c,1320,37,140,41,7,0xffedf3f8);text(c,"Ajustar",1320,38,140,39,20,uitheme::accentInk(),true);text(c,"×",1470,39,65,44,31,uitheme::accentInk(),true);
  int count=int(comp.rounds.size());if(comp.format!="league"&&count){int visible=(std::min)(8,count),start=std::clamp(bracketPhase-3,0,(std::max)(0,count-visible));float width=1428.f/visible;for(int i=0;i<visible;++i){int index=start+i;float x=86+i*width;rounded(c,x,108,width-3,35,6,index==bracketPhase?uitheme::accent():0xffedf3f8);text(c,comp.rounds[index].name,x+5,110,int(width)-13,31,14,index==bracketPhase?uitheme::selectedText():RGB(29,54,77),true);}if(count>8){text(c,"‹",55,109,29,32,24,uitheme::accentInk(),true);text(c,"›",1518,109,29,32,24,uitheme::accentInk(),true);}}
  if(comp.format!="league")bracketHighlights(c,comp);text(c,"Analógico esquerdo / setas · Mover    L2 / R2 · Zoom    Analógico direito · Fases",90,691,1390,12,10,RGB(109,132,152),true);
  if(comp.nodes.empty()&&comp.format!="league"){text(c,"O chaveamento aparecerá quando a estrutura estiver registrada na carreira.",100,380,1400,80,25,RGB(116,138,150),true);return;}
  if(!canvasClip){D3D11_RASTERIZER_DESC desc{};r.raster->GetDesc(&desc);desc.ScissorEnable=TRUE;r.device->CreateRasterizerState(&desc,&canvasClip);}
  if(!canvasClip)return;
  struct RestoreScissors{ID3D11DeviceContext*c;D3D11_RECT rects[16]{};UINT count=16;RestoreScissors(ID3D11DeviceContext*ctx):c(ctx){c->RSGetScissorRects(&count,rects);}~RestoreScissors(){c->RSSetScissorRects(count,rects);}} restoreScissors(c);
  D3D11_RECT clip{LONG(r.left+55*r.scale),LONG(r.top+153*r.scale),LONG(r.left+1545*r.scale),LONG(r.top+(comp.format=="league"?783:691)*r.scale)};if(canvasClip){c->RSSetState(canvasClip);c->RSSetScissorRects(1,&clip);}
  if(comp.format=="league"){
   if(comp.groups.empty()){c->RSSetState(r.raster);return;}auto&g=comp.groups[0];auto xx=[&](float x){return 800+(x-800)*canvasZoom+canvasPanX;};auto yy=[&](float y){return 463+(y-463)*canvasZoom+canvasPanY;};
   auto txt=[&](const std::string&s,float x,float y,int w,int h,int size,COLORREF ink=RGB(52,77,90),bool center=false){scaledText(c,s,xx(x),yy(y),w,h,size,canvasZoom,ink,center);};
   txt("#",85,146,40,28,19);txt("CLUBE",180,146,380,28,19);const char*heads[]={"J","V","E","D","GP","GC","SG","PTS"};for(int i=0;i<8;++i)txt(heads[i],605+i*100.f,146,85,28,19,RGB(116,138,150),true);txt("ÚLTIMAS 5",1420,146,90,28,18);
   for(size_t i=0;i<g.rows.size();++i){auto&t=g.rows[i];float y=180+float(i)*27.5f;bool own=t.id==data.club;auto ink=own?uitheme::selectedText():RGB(52,77,90);r.rectangle(c,xx(75),yy(y),1450*canvasZoom,27*canvasZoom,own?uitheme::accent():i%2?0xffe9f0f4:0xfff8fbfc);if(!t.color.empty())r.rectangle(c,xx(75),yy(y),5*canvasZoom,27*canvasZoom,color(t.color));txt(std::to_string(t.rank),85,y,40,27,20,ink,true);if(t.movement)arrow(c,xx(134),yy(y+14),t.movement>0?1:-1,t.movement>0?0xff4a9f63:0xffcb6568);image(c,"crest",t.id,xx(151),yy(y+1),25*canvasZoom,25*canvasZoom);txt(t.name,188,y,390,27,21,ink);int values[]={t.games,t.wins,t.draws,t.losses,t.gf,t.ga,(t.gf<0||t.ga<0)?-1000:t.gf-t.ga,t.points};for(int j=0;j<8;++j)txt(j==6?(values[j]==-1000?"—":std::to_string(values[j])):num(values[j]),605+j*100.f,y,85,27,21,ink,true);for(size_t j=0;j<t.form.size()&&j<5;++j)rounded(c,xx(1424+float(j)*16),yy(y+9),9*canvasZoom,9*canvasZoom,4.5f*canvasZoom,t.form[j]=='V'?0xff50a26b:t.form[j]=='D'?0xffcf666c:0xffa8b9c4);}
   c->RSSetState(r.raster);r.normal(c);return;
  }

  std::map<int,const clubcomp::BracketNode*>raw;std::map<int,const clubcomp::BracketPosition*>positions;for(auto&n:comp.nodes)raw[n.id]=&n;for(auto&n:bracketScene.nodes)positions[n.id]=&n;
  std::map<std::pair<int,int>,float>columns;for(auto&n:bracketScene.nodes)if(!n.final)columns[{int(n.x),n.round}]=n.x;
  for(auto&col:columns){float x=viewport.X(col.second-132),w=264*viewport.zoom;if(x+w<55||x>1545)continue;rounded(c,x,155,w,534,8,0x66ffffff);r.line(c,x,156,x,689,0xffe2ebf1);}
  for(auto&e:comp.edges){if(!positions.count(e.source)||!positions.count(e.destination))continue;auto&a=*positions[e.source];auto&b=*positions[e.destination];float side=a.x<b.x?1.f:-1.f;float ax=viewport.X(a.x+side*116),ay=viewport.Y(a.y),bx=viewport.X(b.x-side*(b.final?165:116)),by=viewport.Y(b.y),mid=(ax+bx)/2;unsigned tone=e.rank==1?0xff9fb5c4:0xffc9d6df;
   auto src=raw.find(a.id);if(src!=raw.end()&&src->second->tie>=0){auto&t=comp.rounds[src->second->round].ties[src->second->tie];if(t.winner==data.club)tone=uitheme::accent();}
   r.line(c,ax,ay,mid,ay,tone);r.line(c,mid,ay,mid,by,tone);r.line(c,mid,by,bx,by,tone);
  }
  for(auto&n:bracketScene.nodes){auto found=raw.find(n.id);if(found==raw.end())continue;auto&v=*found->second;auto&t=comp.rounds[v.round];const clubcomp::Tie*tie=v.tie>=0?&t.ties[v.tie]:nullptr;if(n.final)bracketFinal(c,comp,tie);else bracketTie(c,comp,n,tie);}
  // Column headings remain visible during vertical panning, inside the canvas.
  r.rectangle(c,55,153,1490,27,0xfff2f7fb);for(auto&col:columns){float x=viewport.X(col.second-132),w=264*viewport.zoom;if(x+w<55||x>1545)continue;scaledText(c,comp.rounds[col.first.second].name,x+3,155,258,23,17,viewport.zoom,RGB(35,61,83),true);}
  c->RSSetState(r.raster);r.normal(c);
  float extent=(std::max)(1.f,bracketScene.y1-bracketScene.y0),visible=510/viewport.zoom;if(extent>visible){float thumb=(std::max)(32.f,510*visible/extent),fraction=std::clamp((viewport.y-bracketScene.y0-visible/2)/(extent-visible),0.f,1.f);rounded(c,1548,181,5,510,2,0xffdce6ee);rounded(c,1548,181+(510-thumb)*fraction,5,thumb,2,uitheme::accent());}
 }
