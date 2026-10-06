# Integração Swiss sobre a base V12 que voltou a abrir

## Estado

Revisão aplicada em `U:\fifa 16`, em 05/10/2026. Dev: `J:\mods\fifa 16\fifa-mods-dev\fifa-mods-dev`, branch `fifa-friends-v12`, base `4693010a0a8c37df94bd6749f4a2e18630eb36f5`. Sem commit ou push.

O build e a conferência de arquivos foram concluídos. **O jogo não foi executado nesta revisão; chegar à seleção de idioma e jogar continuam pendentes de teste pelo usuário.**

## Diferenças em relação à tentativa que travou

A tentativa arquivada reconstruía arquivos BIG inteiros. Em `globalcomponents.big`, o original tem 3.133.128 bytes, declara 3.133.112 no cabeçalho e conserva 18 bytes após o último conteúdo. A reconstrução passou a 3.133.120 bytes, mudou o tamanho declarado e descartou o final original. Isso é uma diferença estrutural concreta; ainda não prova que foi a única causa do travamento antes da seleção de idioma.

Esta revisão preserva **todos os 158 BIG já existentes**, incluindo seus conteúdos APT, cabeçalhos e finais. Só adiciona os 693 arquivos ausentes. Os 40 conflitos internos foram registrados por nome, tipo, tamanho e hash no manifesto. A inicialização das adições nativas saiu da inicialização da DLL e passou para depois do retorno bem sucedido da chamada original `DirectInput8Create`, com uma pequena espera no trabalhador.

Também foi retirada a conversão automática ampla da base de dados. A DB e seu XML atuais permanecem intactos. O VP8 continua desativado, como na base que abriu. Os logs anteriores registram zero hooks do VP8 nas tentativas analisadas; não há evidência para atribuir o travamento ao VP8.

## DLLs: o que foi efetivamente integrado

| Arquivo | Tratamento |
| --- | --- |
| `dinput8.dll` | Recompilado a partir do host original V12. O host recebeu um include e uma chamada após o retorno do DirectInput original. Os demais mecanismos do host e seu `DllMain` foram preservados. |
| Recurso original L9.65 / `dinput8_l9_chain.dll` | Mantido byte a byte, SHA-256 `b6583fc60b5058215b12e90e49e5f1d2a0b5069aa909eab9b916621ad77ac6e2`. |
| `winmm.dll` | Editado sobre o original: DWORD em `0xEC60`, capacidade InitTeams de 7.000 para 16.000. Só dois bytes diferem; desfazer esse DWORD recupera exatamente o hash anterior. |
| `dinput8_orig.dll` | Idêntico entre as entregas; preservado. |

O usuário não possui os fontes C/C++ do Swiss. Por isso, **não houve uma mesclagem integral de fontes das duas DLLs**. O processo foi:

- 49 ajustes de desempacotamento de chaves de uniformes e três ajustes de capacidade de liga reconstruídos em tabelas e rotinas C no host original.
- Terceiro guarda FCE e sua capacidade 10.000 reconstruídos em C, preservando os dois guardas originais.
- Reserva de gravação coordenada em C: aguarda os valores originais instalados pela L9.65 antes de aplicar 3.600.000 / 3.500.000. Não inicia um segundo trabalhador Swiss concorrente para os mesmos endereços.
- Oito rotinas adicionais complexas do Swiss e suas dependências foram extraídas seletivamente do binário compilado: 18 funções, 16.020 bytes de código. O recurso adicional é uma imagem esparsa, sem cabeçalho PE, exportação DirectInput ou ponto de entrada da DLL Swiss.
- Os trabalhadores Swiss duplicados de uniformes, capacidade de liga, FCE e orçamento e o inicializador completo foram excluídos. Importações, relocação, configuração e início dessas funções ficam sob controle do host V12.

Essa extração de funções compiladas continua exigindo teste no jogo. Não é possível assegurar compatibilidade em execução só pela análise estática.

## Funcionalidades incorporadas

| Função | Estado/configuração |
| --- | --- |
| Chaves de uniformes para team IDs acima de 131.071 | Ativa, 49 alterações de `sar` para `shr`. Depende de dados/arquivos de uniformes correspondentes. |
| Lista de seleção de até 32 uniformes por time | Ativa; funções adicionais de lista, carrossel, prévia e confirmação. |
| Capacidade de carreira para ligas maiores | Ativa; lista interna de 30 para 102 posições, visando até 99 times. Outros limites das competições e dados ainda se aplicam. |
| Guarda de consulta na simulação/premiações da carreira | Ativa. |
| Guarda de posição inválida na visão semanal | Ativa. |
| Guarda de remoção de entrada inexistente em lista | Ativa; distinto do guarda original que foi mantido. |
| Terceiro guarda na FootballCompEngzf.dll | Ativo, com limite nativo de formações elevado a 10.000. |
| Placar por liga/torneio | Ativo em BCEnginezf e no executável. Liga 31 → set 4; 53 → 5; 341 → 11; 319 → 12; 66 → 13; 62 → 14. Sem mapeamento, mantém a seleção original. |
| Filtragem opcional de ligas | Implementada, desativada. |
| Roteamento opcional de torneios continentais | Implementado, desativado. |

O limite nativo FCE de 10.000 **não converte o campo formationid da DB**. A base atual tem 11 bits (até 2.047), formações existentes até 899 e zero registros em customformations. Para importar dados que ultrapassem esse esquema será necessária uma integração de DB específica. O conversor original Swiss foi adicionado como ferramenta opcional, sem execução automática.

## Configuração e arquivos visuais

As seções originais do `dinput8_L9.ini`, inclusive as linhas repetidas de categorias em Saisonziele, foram mantidas. A base de IDs de jogadores passou de 350.000 para 460.000; foram adicionadas apenas as seções novas e as reservas configuráveis. O controle `[SwissIntegration] Aktiv=0` permite desligar as adições nativas no próximo início do jogo, sem remover os componentes V12. Isso não desfaz o ajuste do winmm ou do memoryfw; para retorno completo, use o backup.

Em `memoryfw.ini`, somente `SaveLoadPP` passou de 14M para 24M. Foi possível alterar o literal comprimido na posição 5.170 (um byte), sem recomprimir. O tamanho segue 7.974 bytes e a comparação do conteúdo descomprimido confirma apenas essa alteração.

| Arquivos BIG da entrega | Quantidade | Ação |
| --- | ---: | --- |
| Ausentes na base | 693 | Adicionados sem alteração do binário entregue. |
| Já idênticos | 118 | Preservados no jogo. |
| Conflitos de apresentação padrão/estilo | 40 | Originais preservados integralmente; diferenças internas documentadas. |

Os conflitos se concentram na apresentação padrão set 6/set 9 e no estilo global. Não foi aplicada a troca integral de APT/texturas desses estilos. Os conjuntos novos usados pelos mapeamentos Swiss foram adicionados com seus arquivos correspondentes.

## Conferências realizadas

- Compilação do novo código C com `/W4 /WX`, sem erros. O link manteve os avisos já existentes de exportações COM não marcadas PRIVATE.
- Hash dos 415 arquivos do backup inicial conferido.
- Recurso original L9.65 idêntico antes/depois e exportações do host preservadas.
- Novo recurso embutido igual ao recurso extraído e 52 descritores C sem sobreposição entre si.
- 158 BIG originais idênticos; 693 adições com hashes iguais aos da entrega.
- DB, XML, FIFA16.exe, worker de aposentadoria, dinput8_orig, dinput8_patch, Server16Python e lista dos quatro plugins originais preservados.
- Instalador após aplicação: **ToInstall=0, ToArchive=0, 764 arquivos iguais, 20 configurações/localizações preservadas**.
- Nenhuma suíte de testes foi executada e nenhum sucesso de abertura do FIFA foi presumido.

Dois Server16Python remanescentes do jogo fechado impediam a escrita em winmm.dll. Eles foram encerrados para liberar o arquivo. A instalação ficou completa depois disso. O instalador agora conserva logs que estiverem abertos ou sem permissão de movimentação.

## Backup e evidências

Pasta: `J:\mods\fifa 16\estudos fifa 16\backups\integracao-revisada-20261005_223206`.

Ela contém o estado original confirmado, a revisão preparada, manifestos de alterações, auditorias antes/depois, registros do instalador e script de retorno. A tentativa anterior permanece em `integracao-preservada-retorno-20261005_212414`.

Arquivos detalhados no Dev:

- `ModCarrerMode/docs/swiss-assets-manifest.json`: decisão e diferenças internas de cada um dos 851 BIG.
- `ModCarrerMode/docs/swiss-byte-patches.json`: 52 posições, bytes anteriores/novos.
- `ModCarrerMode/docs/swiss-native-resource.json`: funções compiladas incluídas/excluídas e hashes.
- `ModCarrerMode/tools/swiss_integration/`: preparação reproduzível e auditoria dos arquivos.

Para a primeira validação: verificar se chega à seleção de idioma e ao menu. Depois, partida nas ligas mapeadas para verificar placares e seleção de uniformes; por fim, carreira e gravação. Esses resultados devem ser observados no jogo.
