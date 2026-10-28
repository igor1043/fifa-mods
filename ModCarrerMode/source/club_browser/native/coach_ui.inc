// Own layout and data; shares only the verified native actor/camera pipeline.
void drawCoach(ID3D11DeviceContext*c){
 auto&r=renderer;coach.poll(lineup,r.device);int label=0;const auto ink=RGB(48,72,86),muted=RGB(105,129,143),blue=RGB(0,107,172),white=RGB(255,255,255);
 std::wstring subtitle=wide(model.club().name);if(coach.ready){int date=coach.profile.value("date");if(date>20080101){std::wostringstream formatted;formatted<<std::setfill(L'0')<<std::setw(2)<<date%100<<L"/"<<std::setw(2)<<(date/100)%100<<L"/"<<date/10000;subtitle+=L" · "+formatted.str();}int year=coach.profile.value("season_year");if(year>2000)subtitle+=L" · Temporada "+std::to_wstring(year);}rosterHeader(c,label,L"TÉCNICO DO TIME",subtitle,false);
 r.rectangle(c,60,159,442,650,0xfff1f5f5);r.rectangle(c,60,159,442,4,0xff006aae);
 r.rectangle(c,520,159,460,650,0xfff2f5f5);r.rectangle(c,520,159,460,4,0xff006aae);
 for(int i=0;i<3;++i){r.rectangle(c,530+i*147,173,143,40,coach.tab==i?0xff006aae:0xffdce6ea);r.label(c,label++,i==0?L"Resumo":i==1?L"Temporada":L"Escalação",539+i*147,182,130,25,18,coach.tab==i?white:ink,true);}
 if(!coach.ready){r.label(c,label++,wide(coach.error.empty()?"Lendo os dados do técnico desta carreira...":coach.error),85,290,390,130,25,ink,true);return;}
 const auto&p=coach.profile;auto n=[](int v){if(v<0)return std::wstring(L"—");auto s=std::to_wstring(v);for(int i=int(s.size())-3;i>0;i-=3)s.insert(size_t(i),L".");return s;};
 r.label(c,label++,L"TREINADOR",83,187,385,28,18,muted);r.label(c,label++,wide(p.get("name")),83,230,392,77,34,ink);
 int nation=p.value("nation");if(nation>0){gameImage(r.device,coachFlag,art,{"data/ui/imgAssets/flags512x512/f_"+std::to_string(nation)+".dds","data/ui/artassets/countryflags/f_"+std::to_string(nation)+".big"});containImage(c,coachFlag,85,310,41,27);}r.label(c,label++,wide(p.get("country")),nation>0?139.f:84.f,309,nation>0?335.f:391.f,31,22,ink);
 r.rectangle(c,82,356,397,1,0xffc9d8df);
 const std::wstring confidence=p.value("confidence")>=0?n(p.value("confidence"))+L"%":L"—";
 int rep=p.value("reputation");std::wostringstream reputation;if(rep>=0)reputation<<std::fixed<<std::setprecision(1)<<rep*5./1501.<<L" / 5";else reputation<<L"—";auto repText=reputation.str();std::replace(repText.begin(),repText.end(),L'.',L',');
 const std::pair<std::wstring,std::wstring>facts[]={{L"Clube",wide(p.name)},{L"Confiança",confidence},{L"Reputação",repText},{L"Salário mensal",n(p.value("monthly_wage"))},{L"Formação",wide(p.get("formation"))},{L"Estádio",wide(p.get("stadium"))},{L"Capacidade",n(p.value("capacity"))}};
 for(int i=0;i<7;++i){float y=374.f+i*50;r.label(c,label++,facts[i].first,83,y,142,30,18,muted);r.label(c,label++,facts[i].second,232,y,246,42,i==5?17:19,ink,true);if(i<6)r.rectangle(c,83,y+43,394,1,0xffd4dfe3);}
 r.label(c,label++,p.value("monthly_wage")>=0?L"Salário na unidade monetária da carreira":L"— indica informação não registrada na carreira",83,756,395,35,15,muted,true);
 int league=p.value("league_id");if(league>0){gameImage(r.device,coachLeague,art,{"data/ui/imgAssets/careerCompetitionIcons/"+std::to_string(league)+".png","data/ui/imgAssets/league/light/l"+std::to_string(league)+".dds","data/ui/imgAssets/league/dark/l"+std::to_string(league)+".dds"});containImage(c,coachLeague,539,229,43,39);}r.label(c,label++,wide(p.get("league")),592,234,365,41,21,ink);
 if(coach.tab==0){
  r.label(c,label++,L"DESEMPENHO DO CLUBE",540,294,419,30,19,muted);auto stats=p.stats.at("total");const wchar_t*names[]={L"Jogos",L"Vitórias",L"Empates",L"Derrotas",L"Gols pró",L"Gols contra"};
  for(int i=0;i<6;++i){float x=540.f+(i%3)*141.f,y=337.f+(i/3)*96.f;r.rectangle(c,x,y,134,86,0xffe2ebef);r.label(c,label++,names[i],x+5,y+8,124,25,17,muted,true);r.label(c,label++,n(stats[i]),x+5,y+34,124,44,34,blue,true);}
  const wchar_t*venue[]={L"Geral",L"Mandante",L"Visitante"};const char*keys[]={"total","home","away"};
  for(int i=0;i<3;++i){auto s=p.stats.at(keys[i]);float y=552.f+i*54.f;int percent=s[0]>0?int((s[1]*3+s[2])*100./(s[0]*3)+.5):-1;r.label(c,label++,venue[i],540,y,142,27,20,ink);r.label(c,label++,percent<0?L"—":std::to_wstring(percent)+L"%",870,y,88,27,21,blue,true);r.rectangle(c,540,y+33,418,5,0xffdce5e9);if(percent>0)r.rectangle(c,540,y+33,418*percent/100.f,5,0xff0080b8);}
  r.label(c,label++,L"Últimos jogos",540,727,178,28,19,muted);auto form=p.get("form");for(size_t i=0;i<form.size()&&i<5;++i){char ch=form[i];if(ch!='V'&&ch!='E'&&ch!='D')continue;float x=741.f+float(i)*43;r.rectangle(c,x,720,36,36,ch=='V'?0xff378b57:ch=='E'?0xff7a8790:0xffc5454b);r.label(c,label++,std::wstring(1,wchar_t(ch)),x,724,36,28,21,white,true);}
  r.label(c,label++,L"Resultados desta carreira · clube selecionado",540,777,418,24,15,muted,true);
 }else if(coach.tab==1){
  r.label(c,label++,L"COMPETIÇÕES E HISTÓRICO",540,290,418,29,18,muted);
  int total=int(p.competitions.size()+p.history.size())+2,first=coach.scroll;
  for(int i=0;i<8;++i){int at=first+i;float y=331.f+i*54.f;if(at>=total)break;
   if(at==0){r.label(c,label++,L"COMPETIÇÃO               J    V    E    D",543,y,415,26,16,muted);continue;}
   if(at<=int(p.competitions.size())){auto&row=p.competitions[at-1];r.rectangle(c,540,y-2,418,49,0xffe4ecef);r.label(c,label++,wide(row.name)+L" · "+wide(row.status),548,y,402,24,16,ink);std::wstring values=n(row.stats[0])+L"J  "+n(row.stats[1])+L"V  "+n(row.stats[2])+L"E  "+n(row.stats[3])+L"D · "+n(row.stats[4])+L":"+n(row.stats[5])+L" gols · "+(row.stats[0]>0?std::to_wstring(int((row.stats[1]*3+row.stats[2])*100./(row.stats[0]*3)))+L"%":L"—");r.label(c,label++,values,548,y+24,402,21,14,muted);}
   else if(at==int(p.competitions.size())+1){r.label(c,label++,L"TEMPORADA       J    V    E    D    PTS",543,y,415,26,16,muted);}
   else{auto&row=p.history[at-int(p.competitions.size())-2];r.rectangle(c,540,y-2,418,49,0xffe4ecef);r.label(c,label++,L"Temporada "+n(row.season)+L" · "+(row.rank>0?n(row.rank)+L"º":L"—")+L" · "+n(row.titles)+L" títulos",548,y,402,24,18,ink);r.label(c,label++,n(row.stats[0])+L"J  "+n(row.stats[1])+L"V  "+n(row.stats[2])+L"E  "+n(row.stats[3])+L"D · "+n(row.stats[6])+L" pts · "+n(row.stats[4])+L":"+n(row.stats[5])+L" gols",548,y+24,402,21,14,muted);}
  }
  if(p.competitions.empty()&&p.history.empty())r.label(c,label++,L"Sem resultados registrados para este clube.",545,462,409,81,22,ink,true);
  r.label(c,label++,L"↑  ↓  "+std::to_wstring((std::min)(total,first+1))+L"–"+std::to_wstring((std::min)(total,first+8))+L" de "+std::to_wstring(total),540,777,419,24,16,muted,true);
 }else{
  r.label(c,label++,L"TIME TITULAR · "+wide(p.get("formation")),540,291,419,30,19,muted);
  for(size_t i=0;i<p.starters.size();++i){auto&row=p.starters[i];float y=335.f+float(i)*37.f;r.rectangle(c,540,y,418,34,i%2?0xffe2ebef:0xffeaf0f2);r.label(c,label++,std::to_wstring(row.number),547,y+3,34,29,18,blue,true);r.label(c,label++,wide(row.name),588,y+3,315,29,18,ink);r.label(c,label++,n(row.overall),911,y+3,39,29,18,ink,true);}
  if(p.starters.empty())r.label(c,label++,L"Escalação titular indisponível para este clube.",545,460,408,95,23,ink,true);r.label(c,label++,L"Escalação titular salva nesta carreira",540,777,418,24,15,muted,true);
 }
 bool actorReady=coach.submitted&&clubscene::readySequence==coach.submitted;
 if(!actorReady){r.rectangle(c,1030,660,515,118,0xc0122937);r.label(c,label++,wide(coach.modelMessage.empty()?"Preparando "+p.get("name")+"...":coach.modelMessage),1045,678,485,80,24,white,true);}
}
