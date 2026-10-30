// Club totals and the current coach spell are intentionally separate datasets.
std::array<clubgfx::Texture,3> coachCompetitionIcons;
clubgfx::Texture coachPortrait;
ID3D11Device* coachArtDevice=nullptr;
void clearCoachArt(){coachPortrait.clear();coachFlag.clear();coachLeague.clear();for(auto&t:coachCompetitionIcons)t.clear();coachArtDevice=nullptr;}
std::wstring coachNumber(int value){if(value<0)return L"—";auto s=std::to_wstring(value);for(int i=int(s.size())-3;i>0;i-=3)s.insert(size_t(i),L".");return s;}
int coachEfficiency(const clubcoach::Stats&s){return s[0]>0?std::clamp(int((s[1]*3+s[2])*100./(s[0]*3)+.5),0,100):-1;}
void coachCircle(ID3D11DeviceContext*c,float x,float y,float radius,unsigned color){std::vector<std::array<float,2>>points;for(int i=0;i<24;++i){float a=i*6.2831853f/24,b=(i+1)*6.2831853f/24;points.push_back({x,y});points.push_back({x+radius*std::cos(a),y+radius*std::sin(a)});points.push_back({x+radius*std::cos(b),y+radius*std::sin(b)});}renderer.primitive(c,points,color,true);}
void coachSummary(ID3D11DeviceContext*c,int&label,const std::map<std::string,clubcoach::Stats>&stats,const std::string&form,const std::wstring&note){
 auto&r=renderer;const auto ink=RGB(48,72,86),muted=RGB(105,129,143),accent=uitheme::accentInk();const wchar_t*names[]={L"Jogos",L"Vitórias",L"Empates",L"Derrotas",L"Gols pró",L"Gols contra"};
 const auto&total=stats.at("total");
 for(int i=0;i<6;++i){float x=540.f+(i%3)*141.f,y=337.f+(i/3)*96.f;r.rectangle(c,x,y,134,86,0xffe2ebef);r.label(c,label++,names[i],x+5,y+8,124,25,17,muted,true);r.label(c,label++,coachNumber(total[i]),x+5,y+34,124,44,34,accent,true);}
 const wchar_t*venues[]={L"Geral",L"Mandante",L"Visitante"};const char*keys[]={"total","home","away"};
 for(int i=0;i<3;++i){int percent=coachEfficiency(stats.at(keys[i]));float y=552.f+i*54.f;r.label(c,label++,venues[i],540,y,190,27,20,ink);r.label(c,label++,percent<0?L"—":std::to_wstring(percent)+L"%",870,y,88,27,21,accent,true);r.rectangle(c,540,y+33,418,6,0xffdce5e9);if(percent>0)r.rectangle(c,540,y+33,418*percent/100.f,6,uitheme::accent());}
 r.label(c,label++,L"Últimas 5",540,725,178,28,19,muted);
 for(size_t i=0;i<form.size()&&i<5;++i){char ch=form[i];if(ch!='V'&&ch!='E'&&ch!='D')continue;float x=757.f+float(i)*43;coachCircle(c,x,739,16,ch=='V'?0xff378b57:ch=='E'?0xff7a8790:0xffc5454b);r.label(c,label++,std::wstring(1,wchar_t(ch)),x-16,724,32,29,17,RGB(255,255,255),true);}
 r.label(c,label++,note,540,777,418,24,14,muted,true);
}
void coachSeason(ID3D11DeviceContext*c,int&label){
 auto&r=renderer;const auto&p=coach.profile;const auto ink=RGB(48,72,86),muted=RGB(105,129,143),accent=uitheme::accentInk();
 const int total=int(p.competitions.size()+p.history.size()),pages=(std::max)(1,(total+2)/3);coach.scroll=std::clamp(coach.scroll/3,0,pages-1)*3;
 r.label(c,label++,L"COMPETIÇÕES DA TEMPORADA",540,239,418,30,21,ink);
 r.label(c,label++,L"Temporada "+std::to_wstring(p.value("season_year"))+L" · "+std::to_wstring(p.competitions.size())+L" competições",540,276,418,24,16,muted);
 for(int i=0;i<3&&coach.scroll+i<total;++i){int at=coach.scroll+i;float y=313.f+i*147.f;bool current=at<int(p.competitions.size());
  auto stats=current?p.competitions[at].stats:p.history[at-int(p.competitions.size())].stats;
  std::wstring title=current?wide(p.competitions[at].name):L"Temporada "+coachNumber(p.history[at-int(p.competitions.size())].season);
  std::wstring status=current?wide(p.competitions[at].status):L"Histórico · "+coachNumber(p.history[at-int(p.competitions.size())].rank)+L"º · "+coachNumber(p.history[at-int(p.competitions.size())].titles)+L" títulos";
  r.rectangle(c,540,y,418,136,0xffe6edef);r.rectangle(c,540,y,3,136,uitheme::accent());
  int asset=current?p.competitions[at].asset:0;
  if(asset>0){std::string id=std::to_string(asset);gameImage(r.device,coachCompetitionIcons[i],art,{"data/ui/imgAssets/careerCompetitionIcons/"+id+".png","data/ui/imgAssets/league/light/l"+id+".dds","data/ui/imgAssets/league/dark/l"+id+".dds"});containImage(c,coachCompetitionIcons[i],552,y+12,51,50);}
  if(!asset||!coachCompetitionIcons[i].view){r.rectangle(c,555,y+16,44,41,0xfff5f7f8);r.label(c,label++,current?L"C":L"T",555,y+20,44,31,23,accent,true);}
  r.label(c,label++,title,617,y+10,328,28,20,ink);r.label(c,label++,status,617,y+40,328,23,15,muted);
  r.label(c,label++,coachNumber(stats[0])+L" jogos · "+coachNumber(stats[1])+L" V · "+coachNumber(stats[2])+L" E · "+coachNumber(stats[3])+L" D",555,y+68,389,25,17,ink);
  int percent=coachEfficiency(stats);r.rectangle(c,555,y+103,327,7,0xffcedbe1);if(percent>0)r.rectangle(c,555,y+103,327*percent/100.f,7,uitheme::accent());r.label(c,label++,percent<0?L"—":std::to_wstring(percent)+L"%",891,y+90,54,28,20,accent,true);
  r.label(c,label++,L"GP "+coachNumber(stats[4])+L" · GC "+coachNumber(stats[5])+L" · "+coachNumber(stats[6])+L" pontos",555,y+115,386,19,13,muted);
 }
 if(!total){r.label(c,label++,L"Sem competições registradas para este clube.",546,426,406,35,20,ink,true);r.label(c,label++,L"Os resultados aparecerão conforme a carreira avançar.",546,469,406,29,16,muted,true);}
 r.label(c,label++,L"↑  ↓  Página "+std::to_wstring(coach.scroll/3+1)+L" de "+std::to_wstring(pages)+L" · Aproveitamento por pontos",540,777,418,24,15,muted,true);
}
void drawCoach(ID3D11DeviceContext*c){
 auto&r=renderer;coach.poll(lineup,r.device);if(coachArtDevice!=r.device){clearCoachArt();coachArtDevice=r.device;}int label=0;const auto ink=RGB(48,72,86),muted=RGB(105,129,143),white=RGB(255,255,255);
 std::wstring subtitle=wide(model.club().name);if(coach.ready){int date=coach.profile.value("date");if(date>20080101){std::wostringstream formatted;formatted<<std::setfill(L'0')<<std::setw(2)<<date%100<<L"/"<<std::setw(2)<<(date/100)%100<<L"/"<<date/10000;subtitle+=L" · "+formatted.str();}int year=coach.profile.value("season_year");if(year>2000)subtitle+=L" · Temporada "+std::to_wstring(year);}rosterHeader(c,label,L"TÉCNICO DO TIME",subtitle,false);
 r.rectangle(c,60,159,442,650,0xfff1f5f5);r.rectangle(c,60,159,442,4,uitheme::accent());r.rectangle(c,520,159,460,650,0xfff2f5f5);r.rectangle(c,520,159,460,4,uitheme::accent());
 const wchar_t*tabs[]={L"Resumo do time",L"Resumo do técnico",L"Temporada"};for(int i=0;i<3;++i){float x=530.f+clubcoach::tabX[i];int width=clubcoach::tabWidth[i];r.rectangle(c,x,173,float(width),40,coach.tab==i?uitheme::accent():0xffdce6ea);r.label(c,label++,tabs[i],x+4,182,width-8,25,16,coach.tab==i?uitheme::selectedText():ink,true);}
 if(!coach.ready){r.label(c,label++,wide(coach.error.empty()?"Lendo os dados do técnico desta carreira...":coach.error),85,290,390,130,25,ink,true);return;}
 const auto&p=coach.profile;r.label(c,label++,L"TREINADOR",83,187,385,28,18,muted);
 const auto photo=art.game/L"ModCarrerMode/data/manager_market"/wide(clubcoach::portraitFile(p.get("portrait")));
 r.rectangle(c,83,229,110,110,0xffe4ebef);clubgfx::image(r.device,coachPortrait,photo.wstring());
 if(coachPortrait.view)containImage(c,coachPortrait,85,230,106,108);
 else{r.label(c,label++,L"T",86,261,104,45,33,muted,true);}
 r.label(c,label++,wide(p.get("name")),208,232,270,70,29,ink);
 int nation=p.value("nation");if(nation>0){gameImage(r.device,coachFlag,art,{"data/ui/imgAssets/flags512x512/f_"+std::to_string(nation)+".dds","data/ui/artassets/countryflags/f_"+std::to_string(nation)+".big"});containImage(c,coachFlag,209,312,30,21);}r.label(c,label++,wide(p.get("country")),nation>0?250.f:208.f,308,nation>0?228.f:270.f,31,20,ink);r.rectangle(c,82,356,397,1,0xffc9d8df);
 const std::wstring confidence=p.value("confidence")>=0?coachNumber(p.value("confidence"))+L"%":L"—";int rep=p.value("reputation");std::wostringstream reputation;if(rep>=0)reputation<<std::fixed<<std::setprecision(1)<<rep*5./1501.<<L" / 5";else reputation<<L"—";auto repText=reputation.str();std::replace(repText.begin(),repText.end(),L'.',L',');
 const std::pair<std::wstring,std::wstring>facts[]={{L"Clube",wide(p.name)},{L"Confiança",confidence},{L"Reputação",repText},{L"Salário mensal",coachNumber(p.value("monthly_wage"))},{L"Formação",wide(p.get("formation"))},{L"Estádio",wide(p.get("stadium"))},{L"Capacidade",coachNumber(p.value("capacity"))}};
 for(int i=0;i<7;++i){float y=374.f+i*50;r.label(c,label++,facts[i].first,83,y,142,30,18,muted);r.label(c,label++,facts[i].second,232,y,246,42,i==5?17:19,ink,true);if(i<6)r.rectangle(c,83,y+43,394,1,0xffd4dfe3);}r.label(c,label++,p.value("monthly_wage")>=0?L"Salário na unidade monetária da carreira":L"— indica informação não registrada na carreira",83,756,395,35,15,muted,true);
 if(coach.tab==2)coachSeason(c,label);
 else if(coach.tab==1){
  r.label(c,label++,L"PASSAGEM ATUAL NO CLUBE",540,239,418,30,21,ink);
  if(p.value("coach_available")==1){r.label(c,label++,L"Desde "+wide(p.get("coach_since"))+L" · "+coachNumber(p.value("coach_days"))+L" dias no cargo",540,276,418,27,17,muted);coachSummary(c,label,p.coachStats,p.get("coach_form"),p.get("coach_stats_note")=="—"?L"Partidas identificadas nesta passagem do técnico":wide(p.get("coach_stats_note")));}
  else{r.label(c,label++,L"Aguardando os dados do mercado de técnicos.",541,385,417,36,19,ink,true);r.label(c,label++,L"O resumo do time continua disponível na primeira aba.",541,430,417,31,16,muted,true);}
 }else{
  int league=p.value("league_id");if(league>0){gameImage(r.device,coachLeague,art,{"data/ui/imgAssets/careerCompetitionIcons/"+std::to_string(league)+".png","data/ui/imgAssets/league/light/l"+std::to_string(league)+".dds","data/ui/imgAssets/league/dark/l"+std::to_string(league)+".dds"});containImage(c,coachLeague,539,229,43,39);}r.label(c,label++,wide(p.get("league")),592,234,365,41,21,ink);r.label(c,label++,L"DESEMPENHO DO TIME",540,294,419,30,19,muted);coachSummary(c,label,p.stats,p.get("form"),L"Resultados do time nesta temporada da carreira");
 }
 bool actorReady=coach.submitted&&clubscene::readySequence==coach.submitted;if(!actorReady){r.rectangle(c,1030,660,515,118,0xc0122937);r.label(c,label++,wide(coach.modelMessage.empty()?"Preparando "+p.get("name")+"...":coach.modelMessage),1045,678,485,80,24,white,true);}
}
