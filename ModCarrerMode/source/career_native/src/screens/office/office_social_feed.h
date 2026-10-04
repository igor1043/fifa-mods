#pragma once
#include "../competitions/club_competitions_screen.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <vector>

namespace office_social {
struct Player {int id=0;std::string name;};
struct Signals {
    int club=0,competition=0,rank=0,teams=0,played=0,wins=0,draws=0,losses=0,leader_rounds=0;
    int cup_state=0,coach_recent_games=0,coach_recent_points=0;
    int movement_type=0,movement_serial=0; /* 1 arrival, 2 departure, 3 both. */
    int goals_for=0,goals_against=0,form[CLUB_COMPETITION_FORM_SIZE]={2,2,2,2,2};
    int last_valid=0,last_home=0,last_goals_for=0,last_goals_against=0;
    int next_valid=0,next_home=0,next_knockout=0,next_rivalry=0,next_opponent_rank=0,next_date=0;
    int recent_games=0,recent_wins=0,recent_draws=0,recent_losses=0,recent_goals_for=0,recent_goals_against=0;
    int table_points=0,table_leader_points=0,goals_leader_valid=0,goals_leader_goals=0,assists_leader_valid=0,assists_leader_assists=0;
    int manager_record_valid=0,manager_games=0,manager_wins=0,manager_draws=0,manager_losses=0,manager_confidence=-1;
    float league_strength=-1,average_overall=0;
    std::string club_name,league_name,coach_name,movement_in,movement_out,last_opponent,next_opponent,goals_leader_name,assists_leader_name;
    std::vector<Player>players;
    bool table_valid=false,is_group=false,coach_recent_valid=false;
};
enum Source {Supporter=0,Press=1,PlayerVoice=2,ClubVoice=3};
struct Post {std::string name,handle,text;bool verified=false,editorial=false;Source source=Supporter;char initial='?';int theme=-1,specificity=0;uint64_t identity=0;};

inline const std::array<const char*,12>&first_names(){static const std::array<const char*,12>v={
    "Ana","Bruno","Caio","Duda","Enzo","Felipe","Gabriela","Heitor","Isabela","João","Lara","Marcos"};return v;}
inline const std::array<const char*,10>&last_names(){static const std::array<const char*,10>v={
    "Almeida","Barros","Costa","Dias","Freitas","Lima","Moura","Nunes","Ribeiro","Souza"};return v;}
/* 12 x 10 = 120 locally generated, fictional supporter identities. */
inline Post supporter(unsigned index){const auto&first=first_names()[index%first_names().size()];const auto&last=last_names()[(index/first_names().size())%last_names().size()];
    Post p;p.name=std::string(first)+" "+last;p.handle="@"+std::string(first)+"."+last+std::to_string(index%97+1);p.initial=first[0];return p;}
inline const std::array<const char*,6>&publishers(){static const std::array<const char*,6>v={
    "Radar da Carreira","Bola em Pauta","Central da Rodada","Arquibancada FC","Painel do Futebol","Mercado da Bola Virtual"};return v;}
inline const std::array<const char*,6>&publisher_handles(){static const std::array<const char*,6>v={
    "@radardacarreira","@bolaempauta","@centraldarodada","@arquibancadafc","@paineldofutebol","@mercadobolavirtual"};return v;}

/* Eleven themes x eight original fan lines = 88 templates. Placeholders are
 * filled only with values available in the current career snapshot. */
inline const std::array<std::array<const char*,8>,11>&fan_lines(){static const std::array<std::array<const char*,8>,11>v={{
 {{"Hoje é dia de apoiar o $CLUBE. Vamos juntos! 💙","A temporada é longa; seguimos com o $CLUBE até o fim.","Camisa e arquibancada: apoio não falta para o $CLUBE.","Cada rodada conta. Pra cima, $CLUBE!","A torcida continua acreditando no trabalho do time.","Um passo de cada vez: foco na próxima rodada.","Dia de jogo é dia de acreditar no $CLUBE!","Seguimos acompanhando cada capítulo dessa temporada."}},
 {{"São $VITORIAS vitórias na liga. O time encaixou! 🔥","O $CLUBE vive uma boa sequência; que continue assim.","A confiança voltou com esses resultados. Bora manter!","O momento é bom e a tabela começa a sorrir.","Esse ritmo dá esperança para a torcida.","Time consistente e pontuando: é isso que queremos ver.","A fase do $CLUBE merece aplausos hoje 👏","Que sequência! Agora é manter os pés no chão."}},
 {{"A fase pede reação. Ainda dá para virar esse roteiro.","Resultado ruim dói, mas a temporada não acabou.","Hora de ajustar e responder dentro de campo.","A torcida cobra, mas também segue junto. Reage, $CLUBE!","Precisamos voltar a competir melhor na próxima rodada.","Sequência difícil. Que venha uma resposta rápida.","Não era o resultado que queríamos; cabeça erguida.","O momento é de união e trabalho."}},
 {{"Liderança do campeonato! Trabalho forte do elenco e comissão. 🏆","O $CLUBE está no topo: que orgulho acompanhar essa campanha!","Primeiro lugar confirmado na tabela. Agora é defender a posição.","A liderança é fruto de pontos conquistados rodada a rodada.","Que campanha até aqui! O $CLUBE merece curtir esse momento.","No topo da tabela e com a torcida sonhando alto.","O líder tem que manter a concentração. Vamos, $CLUBE!","Segue no topo há $LIDERANCIA_RODADAS rodadas consecutivas."}},
 {{"O $CLUBE está na briga pelas primeiras posições. 👀","A diferença para o topo mantém o campeonato aberto.","Tem disputa lá em cima e o $CLUBE está presente.","Cada ponto pode mudar a corrida pelo título.","Boa campanha: agora é transformar regularidade em arrancada.","A parte de cima da tabela está ao alcance.","Seguimos na perseguição. Nada está decidido.","O campeonato está embolado; pontuar é fundamental."}},
 {{"A tabela preocupa, mas ainda há rodada para reagir.","É hora de somar pontos e subir na classificação.","A luta é dura; cada jogo agora vale muito.","A torcida quer resposta e acredita na recuperação.","Ainda dá para mudar a situação no campeonato.","Pressão na tabela: foco total na próxima partida.","Vamos buscar os pontos que faltam, $CLUBE.","Momento delicado, mas não é hora de abandonar o time."}},
 {{"Já são $GOLS gols marcados: o ataque vem aparecendo! ⚽","O saldo ofensivo do $CLUBE chama atenção.","Quando o time cria e converte, a torcida sente confiança.","Bons números na frente; que o faro de gol continue.","O $CLUBE vem balançando a rede com frequência.","Ataque produtivo pode fazer diferença na reta final.","A bola está entrando e o time ganha confiança.","Mais gols e mais pontos: combinação que a torcida gosta."}},
 {{"Defesa sólida faz diferença numa campanha longa. 🧤","O time vem concedendo poucos gols; bom sinal.","Organização atrás também ganha campeonato.","Segurança defensiva para construir resultado.","A retaguarda está ajudando o $CLUBE a pontuar.","Sofrer menos gols é meio caminho para competir.","Boa proteção da área nesta campanha.","Time compacto, defesa atenta: seguimos."}},
 {{"Vaga no mata-mata confirmada para o $CLUBE! 🏆","Classificação garantida após a fase de grupos.","O $CLUBE avançou de fase; agora começa outro desafio.","A torcida já pode comemorar: vaga assegurada.","Passaporte carimbado para a próxima fase!","Campanha de grupos concluída com classificação.","O $CLUBE segue vivo e classificado na competição.","Próxima fase confirmada. Vamos, $CLUBE!"}},
 {{"Fim da campanha de grupos: o $CLUBE ficou fora das vagas.","Eliminação confirmada na fase de grupos. 😔","Desta vez não deu para avançar; obrigado pelo apoio.","O $CLUBE se despede após a campanha no grupo.","A classificação final encerra a participação do time.","Dói parar aqui, mas a torcida continua junto.","O grupo terminou e o $CLUBE não alcançou a vaga.","Cabeça erguida: a próxima competição já vem aí."}},
 {{"Nos últimos $JOGOS_TECNICO jogos, o time de $TECNICO somou $PONTOS_TECNICO% dos pontos.","O trabalho de $TECNICO rende $PONTOS_TECNICO% de aproveitamento recente.","Recorte dos últimos $JOGOS_TECNICO jogos: $PONTOS_TECNICO% com $TECNICO.","A fase do time sob $TECNICO aparece nos números recentes.","Os resultados recentes dão contexto ao trabalho de $TECNICO.","A comissão de $TECNICO busca manter a evolução da equipe.","O save registra $JOGOS_TECNICO jogos recentes no comando de $TECNICO.","A torcida acompanha o trabalho de $TECNICO rodada a rodada."}}
}};return v;}
inline const std::array<std::array<const char*,4>,11>&desk_lines(){static const std::array<std::array<const char*,4>,11>v={{
 {{"Panorama da temporada: $CLUBE soma $JOGOS jogos na liga.","A campanha do $CLUBE segue em andamento; confira a tabela atual.","Resumo do save: $CLUBE, $JOGOS partidas e saldo $SALDO.","Acompanhe a trajetória do $CLUBE nesta temporada."}},
 {{"Boa campanha: $CLUBE soma $VITORIAS vitórias na liga.","Sequência positiva melhora o cenário do $CLUBE na liga.","Os resultados recentes colocam o $CLUBE em evidência.","Momento de alta: o $CLUBE vem somando pontos."}},
 {{"Resultados recentes aumentam a pressão por reação no $CLUBE.","A sequência não foi favorável; próxima rodada ganha peso.","O $CLUBE busca interromper a série de resultados difíceis.","Semana de ajustes após uma fase abaixo do esperado."}},
 {{"Tabela atualizada: $CLUBE ocupa a liderança do campeonato.","Destaque da rodada: $CLUBE aparece em primeiro lugar.","O $CLUBE sustenta a ponta segundo a classificação do save.","Liderança atual confirmada na tabela da carreira."}},
 {{"Disputa pelas primeiras posições segue aberta para o $CLUBE.","$CLUBE está entre os primeiros colocados da liga.","A classificação mantém o $CLUBE na briga pelo topo.","Corrida pelo título: posição atual do $CLUBE é $POSICAO."}},
 {{"Parte inferior da tabela: a posição do $CLUBE exige atenção.","A classificação coloca o $CLUBE sob pressão nesta rodada.","Cada ponto importa para a recuperação do $CLUBE.","Alerta na tabela: o $CLUBE precisa reagir."}},
 {{"Ataque em destaque: $CLUBE marcou $GOLS gols na liga.","Os gols marcados são um dos pontos fortes da campanha.","Números ofensivos do $CLUBE atualizados após $JOGOS jogos.","O setor ofensivo ajuda a manter o $CLUBE competitivo."}},
 {{"Defesa em foco: saldo atual do $CLUBE é $SALDO.","A solidez defensiva ajuda a explicar a campanha do $CLUBE.","Gols sofridos e saldo entram na análise desta rodada.","A defesa do $CLUBE será observada no próximo compromisso."}},
 {{"Confirmado no save: $CLUBE avançou à fase eliminatória.","Classificação do grupo assegurada pelo $CLUBE.","Próxima fase: o $CLUBE segue na competição.","O cenário da copa mudou; vaga do $CLUBE está confirmada."}},
 {{"Encerrada a participação do $CLUBE na fase de grupos.","Tabela final confirma que o $CLUBE não avançou.","Eliminação registrada no save após o encerramento do grupo.","O $CLUBE termina sua campanha nesta competição."}},
 {{"Recorte do treinador: $TECNICO somou $PONTOS_TECNICO% dos pontos nos últimos $JOGOS_TECNICO jogos.","Os últimos $JOGOS_TECNICO jogos do trabalho de $TECNICO renderam $PONTOS_TECNICO% dos pontos.","Forma recente da equipe sob $TECNICO: $PONTOS_TECNICO% em $JOGOS_TECNICO jogos.","Dados do save: aproveitamento recente de $PONTOS_TECNICO% com $TECNICO."}}
}};return v;}

/* Transfer posts are enabled only after the live roster changes. They avoid
 * inventing fees, destinations or confirmed contract details. */
inline const std::array<const char*,4>&arrival_fan_lines(){static const std::array<const char*,4>v={{
 "Acabei de ver $ENTRADA na lista do $CLUBE. Agora quero ver como vai encaixar em campo. 👀","Bem-vindo ao $CLUBE, $ENTRADA! Tomara que a camisa pese e venha bom futebol.",
 "O elenco ganhou uma opção nova: $ENTRADA. Curioso para ver em qual jogo estreia.","$ENTRADA já aparece no grupo do $CLUBE. Reforço só vira solução quando entrega dentro de campo."}};return v;}
inline const std::array<const char*,4>&departure_fan_lines(){static const std::array<const char*,4>v={{
 "$SAIDA não aparece mais na lista do $CLUBE. Obrigado pelos jogos e boa sorte no próximo passo. 🙏","A saída de $SAIDA muda o elenco; espero que a diretoria tenha um plano para repor essa peça.",
 "Vi que $SAIDA deixou o grupo. Fazia parte da temporada; agora quero saber quem ganha espaço.","Boa sorte, $SAIDA. A torcida vai lembrar da sua passagem pelo $CLUBE."}};return v;}
inline const std::array<const char*,3>&arrival_press_lines(){static const std::array<const char*,3>v={{
 "ELENCO | $ENTRADA aparece na lista atual do $CLUBE. O save não registra taxa ou duração contratual.","ATUALIZAÇÃO | Novo nome no grupo do $CLUBE: $ENTRADA. Ainda sem dados de valores ou destino anterior.","MERCADO | A lista do elenco passou a incluir $ENTRADA; estreia e papel no time seguem em aberto."}};return v;}
inline const std::array<const char*,3>&departure_press_lines(){static const std::array<const char*,3>v={{
 "ELENCO | $SAIDA deixou de constar na lista atual do $CLUBE; destino e termos não aparecem no save.","ATUALIZAÇÃO | O grupo do $CLUBE mudou e $SAIDA não está mais relacionado entre os jogadores.","MERCADO | Saída observada no elenco: $SAIDA. A carreira não informa motivo nem clube de destino."}};return v;}

inline const std::array<std::array<const char*,4>,11>&player_lines(){static const std::array<std::array<const char*,4>,11>v={{
 {{"Grupo unido e concentrado no próximo desafio. Vamos trabalhar!","A gente segue junto pelo $CLUBE, dentro e fora de campo.","Temporada longa; foco e trabalho todos os dias.","O elenco está fechado para buscar nossos objetivos."}},
 {{"A confiança do grupo está alta. Vamos manter esse ritmo! 🔥","Treinamos forte e os resultados estão aparecendo.","Boa fase é mérito coletivo; seguimos com os pés no chão.","O vestiário está feliz com a sequência, mas quer mais."}},
 {{"Sabemos que precisamos responder em campo. Seguimos trabalhando.","O grupo sente os resultados, mas está unido para reagir.","A cobrança faz parte. Vamos corrigir e voltar mais fortes.","Não foi o que queríamos; a resposta vem no trabalho."}},
 {{"Liderança é consequência do trabalho de todo o elenco.","Chegar ao topo é bom; difícil vai ser manter a concentração.","O grupo está feliz com a campanha, mas nada está decidido.","Cada jogador tem sua parte nessa liderança do $CLUBE."}},
 {{"A disputa está aberta e vamos lutar por cada ponto.","O elenco acredita que pode continuar subindo na tabela.","Tem muita rodada pela frente; seguimos acreditando.","Nosso foco é fazer a próxima partida e manter a regularidade."}},
 {{"O momento pede união. Vamos sair dessa situação juntos.","Cada jogo importa agora; o grupo sabe da responsabilidade.","A gente entende a cobrança e trabalha para dar a volta por cima.","Ainda há caminho. O elenco não vai desistir."}},
 {{"Criamos chances e estamos conseguindo transformar em gols.","O ataque trabalha para ajudar o $CLUBE a pontuar.","Quando a equipe toda participa, os gols aparecem.","Bom ver a bola entrando; seguimos buscando evolução."}},
 {{"Defender bem começa com o esforço dos onze em campo.","A equipe está trabalhando para proteger melhor nossa área.","Organização coletiva ajuda todo mundo, não só a defesa.","A meta é manter concentração e ajudar o $CLUBE atrás."}},
 {{"Vaga garantida! O grupo merece comemorar e já pensar no próximo passo. 🏆","A classificação é de todos: elenco, comissão e torcida.","Seguimos na competição; agora é preparar o próximo desafio.","Muito feliz por avançar com o $CLUBE."}},
 {{"Dói não avançar, mas vamos aprender e seguir em frente.","O grupo está frustrado; obrigado a quem apoiou até o fim.","Não era o desfecho que queríamos. Vamos trabalhar para melhorar.","A eliminação pesa, mas o elenco continua unido."}},
 {{"O treinador pede intensidade e o grupo está comprometido.","Estamos trabalhando para transformar as ideias de $TECNICO em resultado.","A comissão e o elenco seguem juntos na preparação.","A confiança no trabalho vem do dia a dia, não só do placar."}}
 }};return v;}
inline const std::array<const char*,4>&player_arrival_lines(){static const std::array<const char*,4>v={{
 "Bem-vindo, $ENTRADA! Vamos ajudar na adaptação ao grupo.","A chegada de $ENTRADA dá mais uma opção para o elenco.",
 "Novo companheiro, novos desafios. Boa sorte com a camisa!","O grupo recebe $ENTRADA de braços abertos. Vamos juntos!"}};return v;}
inline const std::array<const char*,4>&player_departure_lines(){static const std::array<const char*,4>v={{
 "Obrigado pela caminhada, $SAIDA. O grupo deseja sucesso.","A saída de $SAIDA mexe com o elenco; seguimos unidos.",
 "Boa sorte no próximo passo, $SAIDA. Foi bom dividir o vestiário.","Vamos sentir falta de $SAIDA, mas desejamos o melhor."}};return v;}
inline const std::array<std::array<const char*,2>,11>&club_lines(){static const std::array<std::array<const char*,2>,11>v={{
 {{"O $CLUBE segue trabalhando em busca dos objetivos da temporada.","Agradecemos à torcida pelo apoio ao grupo."}},
 {{"O elenco mantém o foco após os bons resultados recentes.","O trabalho continua: queremos sustentar a evolução."}},
 {{"Comissão e elenco trabalham para retomar o melhor desempenho.","O clube reconhece a cobrança e segue focado em reagir."}},
 {{"O $CLUBE alcança a liderança na classificação atual.","Seguimos com humildade e foco após chegar ao topo."}},
 {{"O clube continua na disputa pelas primeiras posições.","Cada rodada será importante na corrida pelo objetivo."}},
 {{"O elenco está mobilizado para buscar pontos e reagir.","O clube mantém confiança no trabalho durante a fase difícil."}},
 {{"O setor ofensivo contribui para a campanha do $CLUBE.","Seguimos buscando eficiência e equilíbrio em campo."}},
 {{"O trabalho defensivo é parte importante do desempenho coletivo.","A comissão segue ajustando a organização da equipe."}},
 {{"Classificação confirmada: o $CLUBE avançou à próxima fase.","O clube agradece a torcida e já prepara o próximo desafio."}},
 {{"A campanha na fase de grupos foi encerrada; o trabalho continua.","O $CLUBE agradece o apoio e vai se preparar para os próximos compromissos."}},
 {{"A comissão técnica segue conduzindo a preparação da equipe.","O clube acompanha os números e a evolução do trabalho."}}
 }};return v;}
inline const std::array<const char*,2>&club_arrival_lines(){static const std::array<const char*,2>v={{
 "O $CLUBE dá as boas-vindas a $ENTRADA, novo integrante do elenco.","Chegada de $ENTRADA: desejamos uma ótima trajetória com a camisa do clube."}};return v;}
inline const std::array<const char*,2>&club_departure_lines(){static const std::array<const char*,2>v={{
 "O clube agradece a $SAIDA pela passagem e deseja sucesso no próximo desafio.","$SAIDA deixa o elenco; o $CLUBE reconhece sua contribuição nesta carreira."}};return v;}

inline void replace_all(std::string&text,const char*token,const std::string&value){size_t at=0,n=strlen(token);while((at=text.find(token,at))!=std::string::npos){text.replace(at,n,value);at+=value.size();}}
inline std::string percent(double value){char b[24]={};sprintf_s(b,"%.0f%%",std::clamp(value,0.0,100.0));return b;}
inline std::string date_label(int raw){int year=raw/10000,month=(raw/100)%100,day=raw%100;if(year<2008||year>2060||month<1||month>12||day<1||day>31)return {};
    char date[16]={};sprintf_s(date,"%02d/%02d/%04d",day,month,year);return date;}
inline uint64_t hash_text(const std::string&s){uint64_t h=1469598103934665603ull;for(unsigned char c:s){h^=c;h*=1099511628211ull;}return h;}
inline uint64_t signal_key(const Signals&s){std::string state;auto add=[&](int value){state+='|';state+=std::to_string(value);};
    const int values[]={s.club,s.competition,s.rank,s.teams,s.played,s.wins,s.draws,s.losses,s.leader_rounds,s.cup_state,s.coach_recent_games,s.coach_recent_points,
        s.movement_type,s.movement_serial,s.goals_for,s.goals_against,s.table_valid,s.is_group,s.coach_recent_valid,
        s.last_valid,s.last_home,s.last_goals_for,s.last_goals_against,s.next_valid,s.next_home,s.next_knockout,s.next_rivalry,s.next_opponent_rank,s.next_date,
        s.recent_games,s.recent_wins,s.recent_draws,s.recent_losses,s.recent_goals_for,s.recent_goals_against,s.table_points,s.table_leader_points,
        s.goals_leader_valid,s.goals_leader_goals,s.assists_leader_valid,s.assists_leader_assists,s.manager_record_valid,s.manager_games,s.manager_wins,s.manager_draws,s.manager_losses,s.manager_confidence};
    for(int value:values)add(value);
    state+='|';state+=std::to_string(s.league_strength);state+='|';state+=std::to_string(s.average_overall);
    for(int result:s.form)add(result);
    uint64_t h=hash_text(state)^hash_text(s.coach_name)^hash_text(s.movement_in)^hash_text(s.movement_out)^hash_text(s.last_opponent)^hash_text(s.next_opponent)^hash_text(s.goals_leader_name)^hash_text(s.assists_leader_name);
    for(const auto&p:s.players){h^=hash_text(std::to_string(p.id)+"|"+p.name);h*=1099511628211ull;}return h;}
inline std::vector<int> active_themes(const Signals&s){std::vector<int>out;if(s.played<=0){if(s.cup_state>0)out.push_back(8);if(s.cup_state<0)out.push_back(9);if((s.coach_recent_valid&&s.coach_recent_games>0)||s.manager_record_valid)out.push_back(10);
        if(s.movement_type&1)out.push_back(11);if(s.movement_type&2)out.push_back(12);if(out.empty())out.push_back(0);return out;}
    int form_count=0,form_points=0,streak_result=2,streak=0;for(int r:s.form)if(r!=2){++form_count;form_points+=r==1?3:r==0?1:0;}
    for(int i=CLUB_COMPETITION_FORM_SIZE-1;i>=0&&s.form[i]!=2;--i){if(streak_result==2)streak_result=s.form[i];if(s.form[i]!=streak_result)break;++streak;}
    if((form_count&&form_points>=form_count*2)||streak_result==1&&streak>=3)out.push_back(1);
    if((form_count&&form_points<=form_count*.6)||streak_result==-1&&streak>=3)out.push_back(2);
    if(s.table_valid&&!s.is_group&&s.rank==1)out.push_back(3);
    if(s.table_valid&&!s.is_group&&s.rank>1&&s.rank<=std::min(4,s.teams))out.push_back(4);
    int danger_slots=s.teams>8?4:2;if(s.table_valid&&!s.is_group&&s.teams>4&&s.rank>s.teams-danger_slots)out.push_back(5);
    if(s.goals_for>=s.played*2)out.push_back(6);
    if(s.goals_against<=s.played/2)out.push_back(7);
    if(s.cup_state>0)out.push_back(8);else if(s.cup_state<0)out.push_back(9);
    if(s.coach_recent_valid&&s.coach_recent_games>0||s.manager_record_valid)out.push_back(10);
    if(s.movement_type&1)out.push_back(11);if(s.movement_type&2)out.push_back(12);
    if(out.empty())out.push_back(0);
    return out;}
inline std::string context_text(const Signals&s){std::string out=s.table_valid?std::to_string(s.rank)+"º lugar":"posição não publicada";if(s.table_valid&&s.is_group)out+=" no grupo";return out;}
inline std::string fill_text(std::string text,const Signals&s,double efficiency){int goal_diff=s.goals_for-s.goals_against;replace_all(text,"$CLUBE",s.club_name.empty()?"seu time":s.club_name);
    replace_all(text,"$LIGA",s.league_name.empty()?"liga":s.league_name);replace_all(text,"$POSICAO",context_text(s));replace_all(text,"$JOGOS",std::to_string(s.played));
    replace_all(text,"$VITORIAS",std::to_string(s.wins));replace_all(text,"$PONTOS",percent(efficiency));replace_all(text,"$APROVEITAMENTO",percent(efficiency));
    double coach_efficiency=s.coach_recent_games>0?s.coach_recent_points*100.0/(s.coach_recent_games*3.0):efficiency;
    replace_all(text,"$JOGOS_TECNICO",std::to_string(s.coach_recent_games));replace_all(text,"$PONTOS_TECNICO",percent(coach_efficiency));
    replace_all(text,"$TECNICO",s.coach_name.empty()?"o treinador":s.coach_name);replace_all(text,"$LIDERANCIA_RODADAS",std::to_string(std::max(1,s.leader_rounds)));
    replace_all(text,"$GOLS",std::to_string(s.goals_for));replace_all(text,"$SALDO",(goal_diff>0?"+":"")+std::to_string(goal_diff));
    replace_all(text,"$ENTRADA",s.movement_in.empty()?"o novo reforço":s.movement_in);replace_all(text,"$SAIDA",s.movement_out.empty()?"o jogador":s.movement_out);return text;}
inline uint64_t post_identity(const Post&p){return hash_text(std::to_string((int)p.source)+"|"+p.handle+"|"+p.text);}

struct Runtime {
    uint64_t key=0,session_salt=(uint64_t)std::chrono::steady_clock::now().time_since_epoch().count();int social_index=0,leader_rounds=0,last_played=-1,last_club=0,last_competition=0;
    int movement_serial=0,movement_type=0,candidate_roster_frames=0;std::string movement_in,movement_out;std::vector<Player>previous_roster,candidate_roster;
    std::array<uint64_t,32>recent={};size_t recent_count=0,recent_at=0;
    std::array<Post,5>posts={};
    int consecutive_wins(const Signals&s)const{int n=0;for(int i=CLUB_COMPETITION_FORM_SIZE-1;i>=0&&s.form[i]==1;--i)++n;return n;}
    void remember(uint64_t id){if(!id)return;recent[recent_at]=id;recent_at=(recent_at+1)%recent.size();recent_count=std::min(recent_count+1,recent.size());}
    bool seen(uint64_t id)const{for(size_t i=0;i<recent_count;++i)if(recent[i]==id)return true;return false;}
    static bool same_roster(const std::vector<Player>&a,const std::vector<Player>&b){return a.size()==b.size()&&std::all_of(a.begin(),a.end(),[&](const Player&p){return std::any_of(b.begin(),b.end(),[&](const Player&q){return p.id==q.id;});});}
    void update(const Signals&input){Signals s=input;if(s.club!=last_club){leader_rounds=0;last_played=-1;last_club=s.club;previous_roster.clear();candidate_roster.clear();candidate_roster_frames=0;movement_type=0;movement_in.clear();movement_out.clear();movement_serial=0;key=0;}
        if(s.competition!=last_competition){leader_rounds=0;last_played=-1;last_competition=s.competition;}
        if(!s.players.empty()){
            if(previous_roster.empty()){previous_roster=s.players;candidate_roster.clear();candidate_roster_frames=0;}
            else if(same_roster(s.players,previous_roster)){candidate_roster.clear();candidate_roster_frames=0;}
            else if(same_roster(s.players,candidate_roster)){
                if(++candidate_roster_frames>=2){std::vector<Player>added,removed;
                    for(const auto&p:s.players)if(std::none_of(previous_roster.begin(),previous_roster.end(),[&](const Player&q){return p.id==q.id;}))added.push_back(p);
                    for(const auto&p:previous_roster)if(std::none_of(s.players.begin(),s.players.end(),[&](const Player&q){return p.id==q.id;}))removed.push_back(p);
                    ++movement_serial;movement_type=0;movement_in.clear();movement_out.clear();
                    /* Ignore multi-row changes; a partial database refresh is
                     * not enough evidence to call it a signing or departure. */
                    if(added.size()<=1&&removed.size()<=1){if(!added.empty()){movement_type|=1;movement_in=added.front().name;}
                        if(!removed.empty()){movement_type|=2;movement_out=removed.front().name;}}
                    previous_roster=s.players;candidate_roster.clear();candidate_roster_frames=0;
                }
            } else {candidate_roster=s.players;candidate_roster_frames=1;}
        }
        s.movement_type=movement_type;s.movement_serial=movement_serial;s.movement_in=movement_in;s.movement_out=movement_out;
        if(s.table_valid&&!s.is_group&&s.played!=last_played){if(s.rank==1)leader_rounds=last_played<0?1:leader_rounds+1;else leader_rounds=0;last_played=s.played;}s.leader_rounds=leader_rounds;
        uint64_t next=signal_key(s);if(next==key)return;key=next;social_index=0;
        uint64_t seed=(next?next:0x50f15e5dull)^session_salt;std::mt19937_64 random(seed);std::array<std::vector<Post>,4>pool;auto themes=active_themes(s);double efficiency=s.played>0?(s.wins*3.0+s.draws)*100.0/(s.played*3.0):0;
        auto add=[&](Source source,int theme,const std::string&name,const std::string&handle,bool verified,const char*line,int specificity){Post p;p.source=source;p.theme=theme;p.name=name;p.handle=handle;p.verified=verified;p.editorial=source==Press;p.specificity=specificity;
            p.initial=name.empty()?'?':name[0];p.text=fill_text(line,s,efficiency);p.identity=post_identity(p);pool[(int)source].push_back(std::move(p));};
        for(int theme:themes){if(theme<=10){for(unsigned line=0;line<fan_lines()[theme].size();++line){if(theme==3&&line==7&&s.leader_rounds<3)continue;
                    for(unsigned person=0;person<first_names().size()*last_names().size();++person){Post p=supporter(person);p.source=Supporter;p.theme=theme;p.text=fill_text(fan_lines()[theme][line],s,efficiency);p.identity=post_identity(p);pool[Supporter].push_back(std::move(p));}}
                for(unsigned line=0;line<desk_lines()[theme].size();++line)for(unsigned outlet=0;outlet<publishers().size();++outlet)add(Press,theme,publishers()[outlet],publisher_handles()[outlet],true,desk_lines()[theme][line],0);
                for(unsigned line=0;line<player_lines()[theme].size();++line)for(const auto&player:s.players){if(player.name.empty())continue;add(PlayerVoice,theme,player.name,"@jogador"+std::to_string(player.id),true,player_lines()[theme][line],0);}
                for(unsigned line=0;line<club_lines()[theme].size();++line)add(ClubVoice,theme,"Clube "+(s.club_name.empty()?std::string("da carreira"):s.club_name),"@clube"+std::to_string(s.club),true,club_lines()[theme][line],0);
            } else {
                const bool arrival=theme==11;const auto&fans=arrival?arrival_fan_lines():departure_fan_lines();const auto&press=arrival?arrival_press_lines():departure_press_lines();
                const auto&voices=arrival?player_arrival_lines():player_departure_lines();const auto&club=arrival?club_arrival_lines():club_departure_lines();
                for(const char*line:fans)for(unsigned person=0;person<first_names().size()*last_names().size();++person){Post p=supporter(person);p.source=Supporter;p.theme=theme;p.specificity=2;p.text=fill_text(line,s,efficiency);p.identity=post_identity(p);pool[Supporter].push_back(std::move(p));}
                for(const char*line:press)for(unsigned outlet=0;outlet<publishers().size();++outlet)add(Press,theme,publishers()[outlet],publisher_handles()[outlet],true,line,2);
                for(const char*line:voices)for(const auto&player:s.players)if(!player.name.empty())add(PlayerVoice,theme,player.name,"@jogador"+std::to_string(player.id),true,line,2);
                for(const char*line:club)add(ClubVoice,theme,"Clube "+(s.club_name.empty()?std::string("da carreira"):s.club_name),"@clube"+std::to_string(s.club),true,line,2);
            }}

        // Story posts use the exact career snapshot instead of broad, reusable
        // filler. Each source gets a distinct voice, while the wording stays
        // grounded in confirmed scores, fixtures, standings and player stats.
        auto story=[&](Source source,int theme,const std::string&name,const std::string&handle,bool verified,const std::string&body){
            if(name.empty()||body.empty())return;Post p;p.source=source;p.theme=theme;p.name=name;p.handle=handle;p.verified=verified;p.editorial=source==Press;p.specificity=3;p.initial=name[0];p.text=body;p.identity=post_identity(p);pool[(int)source].push_back(std::move(p));};
        auto fan_stories=[&](int theme,const std::array<std::string,4>&lines){for(unsigned person=0;person<first_names().size()*last_names().size();++person){Post p=supporter(person);p.source=Supporter;p.theme=theme;p.specificity=3;
                p.text=lines[person%lines.size()];p.identity=post_identity(p);pool[Supporter].push_back(std::move(p));}};
        auto press_stories=[&](int theme,const std::array<std::string,4>&lines){for(unsigned outlet=0;outlet<publishers().size();++outlet)story(Press,theme,publishers()[outlet],publisher_handles()[outlet],true,lines[outlet%lines.size()]);};
        const std::string club=s.club_name.empty()?"o clube":s.club_name;
        const std::string rank=s.table_valid?std::to_string(s.rank)+"º lugar":"posição ainda sem registro";
        const std::string last_score=std::to_string(s.last_goals_for)+" x "+std::to_string(s.last_goals_against);
        const std::string recent=s.recent_games>0?std::to_string(s.recent_wins)+"V, "+std::to_string(s.recent_draws)+"E e "+std::to_string(s.recent_losses)+"D nos últimos "+std::to_string(s.recent_games):std::string();
        if(s.last_valid&&!s.last_opponent.empty()){
            const bool win=s.last_goals_for>s.last_goals_against,draw=s.last_goals_for==s.last_goals_against;
            const std::string result=win?"venceu":draw?"empatou com":"perdeu para";
            const std::string venue=s.last_home?"em casa":"fora de casa";
            const std::string phrase=club+" "+result+" "+s.last_opponent+" por "+last_score+" ("+venue+")";
            std::array<std::string,4>fans,press;
            if(win)fans={"Vitória por "+last_score+" sobre "+s.last_opponent+". Três pontos que valem ouro para o "+club+"! 🔥",
                "O "+club+" bateu "+s.last_opponent+" ("+last_score+") e agora aparece em "+rank+". A tabela já mexeu.",
                "Ganhar de "+s.last_opponent+" por "+last_score+" dá outro peso à próxima rodada. Bora manter.",
                "Placar fechado: "+last_score+" contra "+s.last_opponent+". A torcida queria esses três pontos!"};
            else if(draw)fans={"Um ponto para o "+club+": "+last_score+" diante de "+s.last_opponent+". Seguimos.",
                "Empate com "+s.last_opponent+" por "+last_score+"; agora a posição é "+rank+". Cada ponto conta.",
                "O "+last_score+" com "+s.last_opponent+" deixa a disputa aberta. Próximo jogo virou decisivo pra embalar.",
                "Não foi vitória, mas o "+club+" somou um ponto "+venue+" contra "+s.last_opponent+" ("+last_score+")."};
            else fans={"Derrota por "+last_score+" para "+s.last_opponent+". Dói, mas a resposta tem que vir na próxima.",
                "O "+club+" caiu diante de "+s.last_opponent+" ("+last_score+") e segue em "+rank+". Hora de reagir.",
                "Placar de "+last_score+" contra "+s.last_opponent+". A tabela não espera; precisamos pontuar já.",
                "Resultado ruim para o "+club+": "+last_score+". Que o próximo compromisso seja a virada."};
            press={"RODADA | "+phrase+". "+(recent.empty()?"":("Recorte recente: "+recent+".")),
                "ANÁLISE | "+s.last_opponent+" foi o adversário no "+last_score+"; o "+club+" ocupa "+rank+".",
                "PLACAR | "+club+" "+last_score+" "+s.last_opponent+". Campanha: "+std::to_string(s.wins)+" vitórias, "+std::to_string(s.draws)+" empates e "+std::to_string(s.losses)+" derrotas.",
                "PÓS-JOGO | "+phrase+". "+(s.table_valid?std::to_string(s.table_points)+" pontos em "+std::to_string(s.played)+" jogos.":"A classificação ainda não foi publicada.")};
            fan_stories(20,fans);press_stories(20,press);
            std::string club_post="Balanço da rodada: "+phrase+".";if(s.table_valid)club_post+=" O "+club+" está em "+rank+" com "+std::to_string(s.table_points)+" pontos.";
            story(ClubVoice,20,"Clube "+club,"@clube"+std::to_string(s.club),true,club_post);
            if(s.goals_leader_valid&&!s.goals_leader_name.empty()){
                std::string author=s.goals_leader_name;size_t suffix=author.find(" - ");if(suffix!=std::string::npos)author.resize(suffix);
                std::string handle="@artilheiro"+std::to_string(hash_text(author)%100000);
                for(const auto&p:s.players)if(p.name==author){handle="@jogador"+std::to_string(p.id);break;}
                story(PlayerVoice,20,author,handle,true,"A equipe somou mais um resultado: "+last_score+" contra "+s.last_opponent+". Sigo trabalhando com o grupo para a próxima rodada.");
            }
            for(const auto&player:s.players){if(player.name.empty()||player.name==s.goals_leader_name||player.name==s.assists_leader_name)continue;
                story(PlayerVoice,20,player.name,"@jogador"+std::to_string(player.id),true,"O último placar foi "+last_score+" contra "+s.last_opponent+". Já estamos pensando no próximo compromisso.");}
        }
        if(s.next_valid&&!s.next_opponent.empty()){
            std::string venue=s.next_home?"em casa":"fora de casa",date=date_label(s.next_date);
            std::string occasion=s.next_knockout?"mata-mata":s.next_rivalry>=70?"clássico":"próxima rodada";
            std::string fixture="O próximo compromisso do "+club+" é contra "+s.next_opponent+", "+venue+"";
            if(!date.empty())fixture+=" em "+date;
            if(s.next_knockout)fixture+="; confronto eliminatório";else if(s.next_rivalry>=70)fixture+="; duelo marcado como clássico";
            if(s.next_opponent_rank>0)fixture+="; adversário em "+std::to_string(s.next_opponent_rank)+"º na tabela";
            fixture+=".";
            std::array<std::string,4>fans={"Já anotei: "+club+" x "+s.next_opponent+" "+venue+(date.empty()?"":" em "+date)+". "+(s.next_rivalry>=70?"Clássico é clássico! 🔥":"Hora de chegar junto." ),
                "Próxima parada: "+s.next_opponent+". O "+club+" joga "+venue+(date.empty()?"":" em "+date)+" e não dá pra desligar da tabela.",
                s.next_knockout?"Jogo eliminatório contra "+s.next_opponent+". É decisão; arquibancada tem que pesar.":"Contra "+s.next_opponent+", "+venue+". Se pontuar, o "+club+" mantém o plano vivo.",
                "Olho no calendário: "+fixture};
            std::array<std::string,4>press={"AGENDA | "+club+" encara "+s.next_opponent+" "+venue+(s.next_opponent_rank>0?", atual "+std::to_string(s.next_opponent_rank)+"º colocado":"")+".",
                "PRÉ-JOGO | "+occasion+" à vista: "+club+" x "+s.next_opponent+".",
                "CONFRONTO | "+s.next_opponent+" será o próximo adversário do "+club+"; mando: "+venue+".",
                fixture};
            fan_stories(21,fans);press_stories(21,press);story(ClubVoice,21,"Clube "+club,"@clube"+std::to_string(s.club),true,fixture);
        }
        if((s.goals_leader_valid&&!s.goals_leader_name.empty())||(s.assists_leader_valid&&!s.assists_leader_name.empty())){
            std::string scoring,assist;
            if(s.goals_leader_valid&&!s.goals_leader_name.empty())scoring=s.goals_leader_name+" lidera os gols com "+std::to_string(s.goals_leader_goals)+".";
            if(s.assists_leader_valid&&!s.assists_leader_name.empty())assist=s.assists_leader_name+" lidera as assistências com "+std::to_string(s.assists_leader_assists)+".";
            std::string recap=scoring;if(!assist.empty()){if(!recap.empty())recap+=" ";recap+=assist;}
            std::array<std::string,4>fans={scoring.empty()?assist:scoring+" Artilharia atualizada no elenco! ⚽",
                assist.empty()?scoring:assist+" Passe final também decide campeonato.",
                "Números do ataque do "+club+": "+recap,
                "Quem está decidindo? "+recap};
            std::array<std::string,4>press={"RAIO-X OFENSIVO | "+recap,
                "ARTILHARIA | "+(scoring.empty()?"Sem artilheiro identificado no recorte.":scoring),
                "ASSISTÊNCIAS | "+(assist.empty()?"Liderança ainda sem dado confirmado.":assist),
                club+": "+recap};
            fan_stories(22,fans);press_stories(22,press);story(ClubVoice,22,"Clube "+club,"@clube"+std::to_string(s.club),true,"Destaques estatísticos do elenco: "+recap);
            std::string goal_author=s.goals_leader_name,assist_author=s.assists_leader_name;size_t suffix=goal_author.find(" - ");if(suffix!=std::string::npos)goal_author.resize(suffix);
            suffix=assist_author.find(" - ");if(suffix!=std::string::npos)assist_author.resize(suffix);
            std::string author=!goal_author.empty()?goal_author:assist_author;
            std::string handle="@elenco"+std::to_string(hash_text(author)%100000);for(const auto&p:s.players)if(p.name==author){handle="@jogador"+std::to_string(p.id);break;}
            bool is_scorer=!goal_author.empty()&&author==goal_author,is_creator=!assist_author.empty()&&author==assist_author;std::string player_stat="Meu recorte na temporada: ";
            if(is_scorer)player_stat+=std::to_string(s.goals_leader_goals)+" gols";
            if(is_scorer&&is_creator)player_stat+=" e ";
            if(is_creator)player_stat+=std::to_string(s.assists_leader_assists)+" assistências";
            player_stat+=". Sigo trabalhando para ajudar o "+club+".";
            story(PlayerVoice,22,author,handle,true,player_stat);
        }
        if(s.manager_record_valid&&s.manager_games>0){
            std::string coach=s.coach_name.empty()?"o treinador":s.coach_name;
            std::string record=coach+" soma "+std::to_string(s.manager_wins)+"V, "+std::to_string(s.manager_draws)+"E e "+std::to_string(s.manager_losses)+"D em "+std::to_string(s.manager_games)+" jogos na temporada.";
            story(Press,23,"Painel do Futebol","@paineldofutebol",true,"COMANDO | "+record+(s.manager_confidence>=0?" Confiança da diretoria: "+std::to_string(s.manager_confidence)+"/100.":""));
            story(ClubVoice,23,"Clube "+club,"@clube"+std::to_string(s.club),true,"Recorte da temporada: "+record);
        }
        if(s.table_valid){
            int points=s.table_points>0?s.table_points:s.wins*3+s.draws;std::string league=s.league_name.empty()?"classificação":s.league_name,points_gap;
            if(s.table_leader_points>=points)points_gap=" Diferença para a liderança: "+std::to_string(s.table_leader_points-points)+" ponto(s).";
            std::string table_line=club+" ocupa "+rank+" na "+league+": "+std::to_string(points)+" pontos em "+std::to_string(s.played)+" jogos."+points_gap;
            std::array<std::string,4>fans={"Abri a tabela: "+table_line+" Ainda tem campeonato pela frente.",
                "A posição do "+club+" é "+rank+"; são "+std::to_string(points)+" pontos. Próxima rodada pode mudar tudo.",
                "Conferi os números: "+std::to_string(s.wins)+" vitórias, "+std::to_string(s.draws)+" empates e "+std::to_string(s.losses)+" derrotas. "+points_gap,
                "A briga em "+league+" está assim: "+table_line};
            std::array<std::string,4>press={"TABELA | "+table_line,
                "NÚMEROS | "+std::to_string(s.wins)+"V "+std::to_string(s.draws)+"E "+std::to_string(s.losses)+"D; "+std::to_string(s.goals_for)+" gols pró e "+std::to_string(s.goals_against)+" sofridos.",
                "CLASSIFICAÇÃO | "+club+" em "+rank+" após "+std::to_string(s.played)+" partidas."+points_gap,
                "RECORTE DA LIGA | "+table_line};
            fan_stories(24,fans);press_stories(24,press);
            story(ClubVoice,24,"Clube "+club,"@clube"+std::to_string(s.club),true,"Situação atual na tabela: "+table_line);
            for(const auto&player:s.players){if(player.name.empty())continue;story(PlayerVoice,24,player.name,"@jogador"+std::to_string(player.id),true,
                "A tabela mostra o "+club+" em "+rank+" com "+std::to_string(points)+" pontos. O grupo segue concentrado em somar na próxima rodada.");}
        }
        for(auto&by_source:pool)std::shuffle(by_source.begin(),by_source.end(),random);std::vector<Post>selected;
        for(auto&by_source:pool)std::stable_sort(by_source.begin(),by_source.end(),[](const Post&a,const Post&b){return a.specificity>b.specificity;});
        auto take=[&](Source source,int theme,size_t limit){auto&items=pool[(int)source];size_t added=0;for(const auto&p:items){if(added>=limit||selected.size()>=posts.size())break;if(theme>=0&&p.theme!=theme)continue;
                if(seen(p.identity)||std::any_of(selected.begin(),selected.end(),[&](const Post&q){return q.identity==p.identity;}))continue;selected.push_back(p);remember(p.identity);++added;}};
        auto source_count=[&](Source source){return (size_t)std::count_if(selected.begin(),selected.end(),[&](const Post&p){return p.source==source;});};
        auto select_source=[&](Source source,size_t desired,const int*themes,size_t theme_count){
            while(source_count(source)<desired&&selected.size()<posts.size()){size_t before=selected.size();
                for(size_t i=0;i<theme_count&&selected.size()<posts.size();++i){take(source,themes[i],1);if(selected.size()>before)break;}
                if(selected.size()==before)take(source,-1,1);if(selected.size()==before)break;
            }};
        if(s.movement_type){int preferred=(s.movement_type&1)?11:12;take(PlayerVoice,preferred,1);take(Supporter,preferred,1);take(Press,preferred,1);take(ClubVoice,preferred,1);
            if(s.movement_type==3){take(PlayerVoice,12,1);take(Supporter,12,1);take(Press,12,1);take(ClubVoice,12,1);}}
        else {
            const int player_topics[]={22,20,24,23},club_topics[]={21,20,22,24,23},supporter_topics[]={20,21,22,24},press_topics[]={20,21,22,24,23};
            select_source(PlayerVoice,2,player_topics,_countof(player_topics));select_source(ClubVoice,1,club_topics,_countof(club_topics));
            select_source(Supporter,1,supporter_topics,_countof(supporter_topics));select_source(Press,1,press_topics,_countof(press_topics));
            const Source fill_order[]={ClubVoice,Supporter,Press,PlayerVoice};
            while(selected.size()<posts.size()){size_t before=selected.size();for(Source source:fill_order){take(source,-1,1);if(selected.size()>=posts.size())break;}if(selected.size()==before)break;}
        }
        if(selected.size()<posts.size())for(int source=0;source<4&&selected.size()<posts.size();++source)take((Source)source,-1,1);
        for(size_t i=0;i<posts.size();++i)posts[i]=selected.empty()?Post{}:selected[std::min(i,selected.size()-1)];
    }
};

inline uint64_t followers(const Signals&s){double base=45000.0+std::max(0.f,s.league_strength)*11500.0+s.average_overall*5700.0;
    double adjustment=1.0;if(s.table_valid&&!s.is_group&&s.teams>1){double rank_quality=(double)(s.teams-s.rank)/(s.teams-1)-.5;adjustment+=rank_quality*.22;}
    if(s.played>0)adjustment+=std::clamp(((s.wins*3.0+s.draws)/(s.played*3.0)-.5)*.18,-.09,.09);
    return (uint64_t)std::clamp(base*adjustment,12000.0,25000000.0);}
inline std::string format_followers(uint64_t value){char raw[32]={};sprintf_s(raw,"%llu",(unsigned long long)value);std::string out=raw;for(int i=(int)out.size()-3;i>0;i-=3)out.insert((size_t)i,".");return out;}
} // namespace office_social
