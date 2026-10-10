# Prompt reutilizável — converter mascote para FIFA 16

Copie o texto abaixo para uma nova conversa e preencha os campos.

---

Quero converter este mascote para FIFA 16, usando a mesma implementação que funciona para Flamengo, Palmeiras e Atlético Mineiro.

- Arquivo ZIP/FBX/OBJ: **<caminho>**
- Clube: **<nome>**
- ID confirmado no FIFA 16: **<ID>**
- Pasta de saída do pacote: **<caminho>**
- Jogo: **U:\fifa 16**
- Projeto de desenvolvimento: **U:\mods\FIFA Friends V12** (confira se continua nesse caminho)
- Referência visual aprovada: **<imagem/caminho, se houver>**

Faça a conversão completa, com as seguintes regras:

1. Inspecione o ZIP com extração segura. Identifique o modelo e as imagens pela ligação dos materiais do FBX, não pela ordem dos arquivos. A imagem de cor/basecolor é diferente do mapa de normais. Preserve a imagem de cor enviada; não substitua por uma textura antiga do clube.
2. Liste malhas, materiais, camadas UV, unidades, armature e pesos existentes. Não afirme que o FBX tem rig só porque o nome do arquivo contém ballboy. Se houver rig e pesos válidos, preserve-os. Se não houver, use uma referência FIFA visualmente aprovada e transfira pesos com revisão anatômica; confira braços, pernas, tronco e cabeça separadamente. Não copie pesos atravessando uma perna para a outra. Cabeças grandes de mascotes devem manter a forma e ter influência rígida da cabeça quando adequado, com cuidado na junção do pescoço.
3. Use o rig FIFA 16 de 31 ossos e a ordem de índices do template auditado. Preserve os pivôs aprovados e converta as unidades com escala uniforme. O modelo deve ter no máximo 2 m, sem achatamento por escala diferente entre eixos.
4. Preserve as ilhas UV. Confira a convenção vertical do FBX e do RX3/DDS. No Galo, o FBX usava V de origem inferior e o FIFA precisava de **V_exportado = 1 - V_FBX**. Aplicar a inversão duas vezes também é um erro: confira o estado da fonte e a imagem renderizada antes de decidir. Não refaça o unwrap mantendo uma textura que pertence ao unwrap anterior.
5. Compare um render da fonte com um render do RX3 exportado, usando a textura realmente decodificada do pacote instalado e a convenção de amostragem do FIFA. Confira bico/rosto, crista, escudo, camisa, shorts, meias, mãos e pés. Mostre as imagens lado a lado para minha revisão.
6. Empacote as texturas RX3 com os descritores de **16 bytes por nível de mipmap**, incluindo os níveis menores. Não concatene apenas os blocos DDS: isso fez o motor ler bytes de imagem como dimensões gigantes, travar e derrubar o FPS. Use um template válido para o cabeçalho inicial e valide pitch, linhas, tamanho dos dados, contagem de níveis e limites do arquivo. A cor, normais e máscara/coeficientes devem ocupar os slots corretos do material. Mantenha a qualidade adequada ao modelo e os limites do jogo.
7. Valide a malha relendo o RX3 gerado: índices de triângulos dentro dos limites, números finitos, limite de vértices do formato de índices, exatamente quatro entradas de influência por vértice com zeros de preenchimento, no máximo quatro pesos ativos e soma quantizada exata de 255. Todos os ossos usados devem existir no rig. Valide model.rx3 e model_animated.rx3, não apenas o preview FBX.
8. Entregue **model.rx3, model_animated.rx3 e textures.rx3** em **data/sceneassets/mascot/<ID>/**. Documentação, renders, backups e projeto editável devem ficar fora do pacote a copiar para o jogo. Faça backup antes de substituir o mascote instalado e sincronize o projeto de desenvolvimento.
9. Preserve o funcionamento e o desempenho da DLL: um único mascote do mandante, demais fotógrafos/gandulas normais e fallback seguro para clubes sem pasta, sem modelo ou sem textura válida. Reconheça os pacotes válidos por ID de clube, sem uma lista limitada a Flamengo/Palmeiras. Não faça buscas em disco, recargas de recursos, recompilação Lua ou varreduras de identidade a cada quadro. Não altere os hooks de animação aprovados sem necessidade demonstrada.
10. O mascote pode espelhar a torcida, mas **não pode sentar**. Rejeite postura sentada e transições em que as duas coxas ficam horizontais ou a bacia baixa como numa pose sentada. Se não houver pose segura, mantenha a última pose em pé ou a pose neutra. Preserve a comemoração de gol do mandante por 26 segundos.
11. Escolha a posição uma vez no início da partida, atrás das placas do gol que o mandante ataca. Use a posição aprovada em 75% dos sorteios e as alternativas na mesma linha de fundo nos demais. Não sorteie de novo a cada quadro/replay. Na troca de lado, mantenha a distância lateral escolhida e acompanhe o novo gol atacado. A configuração atual usa X atrás das placas em ±5850 cm, Z preferencial +3150 cm e alternativas +900/+1500/+2100/+2700 cm; confira a adequação visual ao estádio antes de ampliar a regra.
12. Faça verificações apropriadas e confira os logs da nova sessão. O arquivo existir e passar no parser não comprova aparência ou FPS no jogo. Informe o que foi validado e o que depende da minha inspeção visual. Para trocar DLL ou descartar recursos em cache, peça que eu feche e reabra o FIFA; não controle meu computador. Não faça commit/push sem meu pedido.

Ao terminar, mostre o render comparativo, os caminhos do pacote e os registros de validação. Se uma falha aparecer só no clube novo enquanto Flamengo continua funcionando, compare primeiro o RX3 do modelo e a estrutura das texturas com um pacote funcional antes de reescrever a DLL.

---

## Referências locais desta conversão

- Fonte aprovada da DLL: `U:\mods\FIFA Friends V12\ModCarrerMode\source\mascot_photographer`.
- Implementação atual: `U:\mods\FIFA Friends V12\ModCarrerMode\source\mascot_photographer`.
- Diagnóstico e renders do Atlético: `U:\fifa 16\ModCarrerMode\source\mascot_package_v15\texture_repair`.
- Ferramenta de rig: `J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster`.
- Clube Atlético Mineiro: ID **1035**. As texturas dos ZIPs `MASCOTE defitivo.obj.zip` e `MASCOTE.obj.zip` eram idênticas; o erro visual veio da convenção UV da conversão.

## Limitação confirmada após teste da versão 16

O usuário confirmou que o mascote ainda faz pose sentada. O filtro geométrico da versão 16 passou em testes sintéticos, mas **não resolveu no jogo**. Não tratar a proibição de sentar como validada. Uma solução futura precisa ser conferida com os clipes nativos reais e no jogo.
