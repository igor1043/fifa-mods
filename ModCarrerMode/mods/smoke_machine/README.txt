Maquina de fumaca / lancador de pirotecnia

Modelo FBX fornecido convertido para RX3 estatico, sem esqueleto.
Texturas de cor e normal preservadas, com mipmaps e acabamento nativo.
Altura aproximada: 55 cm, base centralizada no chao com elevacao de 2 cm.
20 maquinas: oito laterais e doze atras dos gols, cobrindo todos os pontos atuais de emissao.
Malha otimizada: 3.329 triangulos por maquina, 66.580 triangulos no conjunto completo.
Uma malha e um pacote de texturas compartilhados entre as instancias.

DLL unica: smoke_machine.dll. Configuracao local: smoke_machine.ini.
Segue [match] pyrotechnics do controle do Server16 e [pyro] enabled do modulo de fogos.
Nao aparece na previa KickOffHub ou selecao de equipes; conserva a maquina durante pausa/replay da partida.
O modulo adiciona os equipamentos fisicos; disparos e cores continuam sob responsabilidade de stadium_pyrotechnics.dll.
Nao depende de clube, estadio ou competicao.

Feche e abra o FIFA para carregar a DLL e os assets novos.
Log: ModCarrerMode/logs/smoke_machine.log.
Validacoes de conversao, Lua 5.1, pontos de emissao e compilacao passaram.
A visualizacao dentro do FIFA precisa ser confirmada no jogo.

Quatro maquinas internas laterais a -14/+14 metros; nenhuma no meio-campo.
Oito bases laterais a 35 m do eixo do campo: 1 metro para fora da linha lateral, com saidas dos efeitos alinhadas.

Equipamentos de pirotecnia para qualquer time; cores e eventos definidos pelo mandante.

Cada maquina corresponde a um emissor: 20 na abertura, 12 atras dos gols no gol do mandante.
Origem na boca da maquina (57 cm de altura); foguete 12 cm, papel 3 cm; fumaca com crescimento ate nuvem densa.
PARTICLE_AUDIT no log de pirotecnia verifica particulas uma vez por disparo. Menu de pausa interrompe o show em curso.

Cada maquina corresponde a um emissor: 20 na abertura, 12 atras dos gols no gol do mandante.
Origem na boca da maquina (57 cm de altura); foguete 12 cm, papel 3 cm; fumaca com crescimento ate nuvem densa.
PARTICLE_AUDIT no log de pirotecnia verifica particulas uma vez por disparo. Menu de pausa interrompe o show em curso.

Carregamento: ativacao Lua na thread da cena, retry em nova VM/cena, deteccao nativa sem booleano antigo, guardas sem bytes apos o RET.
Diagnostico: asset_files, hook_pending, lua_ready scene_thread, model_deferred e machines_placed.
