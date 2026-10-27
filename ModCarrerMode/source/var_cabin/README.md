# Cabine do VAR — FIFA 16

Usa o OBJ Cabine do Var do pacote CABINE DO VAR 2, fornecido em 14/10/2026, com painéis espelhados nas laterais, fundo e teto. O modelo anterior foi substituído nas rotas ativas; os originais e backups foram preservados. A prévia relê o RX3 e sua textura convertida. A aparência final do material no FIFA aguarda a próxima partida.

A versão 3 mostra a cabine somente no Campeonato Brasileiro Série A (ID 7) e Série B (ID 83), confirmados no banco instalado. A DLL consulta o ID da partida em wvWipe.leagueID, antes de getTournamentGraphics: uma troca de gráficos, a liga do clube ou um amistoso não habilitam a cabine. Copas, estaduais, Séries C/D e demais competições ficam excluídos. ID ausente ou inválido também mantém a cabine oculta. O filtro é reavaliado no início de cada protótipo e a cada segundo, incluindo trocas de partida na mesma sessão. O filtro da versão 3 foi mantido na troca do modelo.

O RX3 tem 12,324 vértices e 19,447 triângulos, com altura de 200 cm, largura de 132,6 cm e profundidade de 110,8 cm. As posições de todos os triângulos são idênticas às da cabine anterior após a decodificação RX3. Foram restauradas as UVs originais do OBJ que correspondem ao novo COLOR.png e nm.png fornecidos em 15/10/2026. O padrão azul e os logotipos vêm das novas imagens; as tangentes foram recalculadas para esse mapeamento. Os 48 triângulos dos painéis espelhados e o mapa de coeficientes foram preservados. A textura continua em DXT5 com cor em 1024 × 2048, normais em 512 × 1024 e coeficientes em 256 × 512, todos com mipmaps completos. O arquivo textures.rx3 permanece com 3.670.960 bytes (cerca de 3,5 MiB).

A posição atual é X=0, Y=2, Z=4600 cm, centralizada na linha do meio-campo na lateral positiva. A rotação é 3,141593 radianos (180 graus), com o monitor voltado para o gramado. O eixo X acompanha o comprimento do campo e Z sua largura. O módulo não troca de lado no intervalo. O mesmo objeto estático vale durante partida, pausa e replay; a posição é independente do relógio.

Arquivos:

- data/sceneassets/var_cabin/model.rx3 e textures.rx3
- ModCarrerMode/mods/var_cabin/var_cabin.dll (ativa no próximo início)
- ModCarrerMode/mods/var_cabin/var_cabin.lua e var_cabin.ini
- ModCarrerMode/logs/var_cabin.log
- Lua adicional ao final de data/fifarna/lua/assets/sle.lua

O protótipo usa o tipo 3, variação 1, enquanto as câmeras normais ficam na variação 0. O Lua cria a instância pelas funções nativas Create/AddSubObject. A DLL acrescenta um registro privado temporariamente ao construtor nativo e devolve a lista original após a chamada. Mantém o callback dos objetos de entrada e o ponto de seleção do mascote. A notificação nativa de carregamento é enviada somente depois de todos os cinco recursos estarem prontos; isso permite adicionar o modelo depois da criação inicial da cena.

Configuração em var_cabin.ini, relida a cada segundo sem reiniciar:

- x_cm: distância do meio-campo (positivo ou negativo)
- z_cm: distância lateral; 4600 é a posição atual
- ground_lift_cm: ajuste do piso, atualmente 2 cm
- yaw_radians: 0 para frente +Z; 3.141593 para frente -Z
- enabled: 0 esconde a cabine na sessão e nas próximas partidas

Compilação: executar build.cmd com MSVC x64 no caminho configurado. Os conversores incluídos precisam do Blender, Pillow/numpy e do bundle local J:/mods/fifa 16/02_Ferramentas/mascot_rig_adjuster. A conversão e as prévias estão em J:/mods/fifa 16/estudos fifa 16/35_CABINE_VAR_20261013. Originais FBX/JPG/PNG foram preservados.

Validação da versão 3: compilação MSVC /W4 /WX; teste do leitor nativo nas estruturas Lua 5.1 x64, IDs de -1 a 2500, transições de competição e dados inválidos; teste Lua 5.1 de amistoso com gráficos da Série A, outra liga com gráficos da Série B e falha de consulta. As variações normais de câmera, mascote e objetos de entrada foram preservadas. O log inclui competition_id e competition_allowed para confirmar a decisão na partida.

Para desativar agora, alterar enabled=0 no INI. Para desativar após reiniciar, comentar apenas var_cabin\var_cabin.dll na lista enabled.txt. Para remover, utilizar o script Desinstalar.ps1 após fechar o FIFA. Os backups preservam os demais mods anteriores à instalação; restaurar sle.lua inteiro manualmente pode remover alterações posteriores de outros mods.

Modelo 2: fontes, conversão, prévias e backup em J:/mods/fifa 16/estudos fifa 16/41_CABINE_VAR_MODELO2_20261014. O ponto de posição, a rotação e a DLL v3 foram preservados. A revisão do modelo entra na próxima abertura do FIFA. A pasta ativa contém somente model.rx3 e textures.rx3; as revisões anteriores ficam no backup externo ao jogo.

Revisão 4: Lua preparado no callback da cena, confirmação dos indicadores de prontidão, nova tentativa após indisponibilidade temporária e criação vinculada à tabela da cena atual. Um booleano de uma partida anterior não impede a criação na seguinte. Os wrappers e atores pendentes não são duplicados. O recurso privado é atualizado depois do Lua, mesmo quando o motor já inicializou sua variação como câmera. As competições permitidas continuam sendo 7 e 83. Consulte `../common/README.md` para testes e limites.

Texturas vigentes desde 15/10/2026: COLOR.png e nm.png, extraídas de Stands e Tex do var.rar. Conversão, fontes e backup em J:/mods/fifa 16/estudos fifa 16/58_VAR_TEXTURAS_20261015. O encaixe foi conferido nas prévias frontal/traseira do RX3; a verificação visual no FIFA aguarda a próxima sessão.
