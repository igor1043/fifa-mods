# Entrada 3D por ID direto — 18/10/2026

O Server16 identifica a competição (`TOURNAME`) e a fase (`TOURROUNDID`) da partida. O arquivo `U:\fifa 16\FSW\settings.ini`, sincronizado do INI da atualização, fornece os IDs aceitos nas seções `[movies]`, `[Scoreboard]` e `[comp]`. Os nomes de vídeo, placar e estádio não são usados como caminhos de modelos.

Os pacotes ficam em `data/sceneassets/entrance_props/competitions/<ID_ATUAL>/`. O nome da pasta é exatamente o ID do CompData instalado, tanto para competições quanto para fases. Não existe tabela de conversão. O TXT `REFERENCIA_IDS.txt` lista os IDs atuais para consulta e não participa da seleção.

Quando a partida informa uma fase, somente a pasta desse ID pode fornecer o modelo. Sem fase, somente a pasta da competição é consultada. O ID precisa estar no INI e o pacote precisa ser válido. Uma fase sem modelo próprio não herda o modelo principal. Sem pacote para o ID selecionado, não são exibidos arco nem placas. O ID 0 é excluído.

Em amistosos, sem competição/fase, dois clubes da mesma liga usam o contexto verificado dessa liga. O Server16 consulta `leagueteamlinks` e encontra o nó em `compobj.txt`: liga `7` → objeto `C7` → ID `1761` → pasta `competitions/1761`. O nó precisa existir no `settings.ini`. Ligas diferentes, informações ausentes, liga sem nó único ou pacote ausente ficam sem entrada. Uma competição real, incluindo uma copa sem modelo, nunca é substituída pela liga dos clubes. Essa regra não habilita a cabine do VAR.

Cada pacote contém `model.rx3`, `template.rx3` e `asset.ini`. A DLL mantém a validação nativa de tamanhos, SHA-256, malha, textura e posições dos escudos. Um pacote explícito inválido é recusado. O cache dos emblemas de mandante/visitante é gerado em `fixtures/` dentro da pasta numérica selecionada.

IDs atuais: Série A `1761`, Série B `1764`, Série C `1770`, Série D `1780` e Paulista `2348`. Uma fase sem ID próprio no INI utiliza o pacote principal. Nomes diferentes em `[movies]` e `[Scoreboard]` permanecem como escritos no arquivo original. Consulte `../../docs/COMPDATA.md` para instalar a base completa.

O botão de objetos de abertura continua usando `[match] entrance_props` de `ModCarrerMode/config/match_presentation.ini`. Essa opção habilita/desabilita a exibição; não redireciona competições. O JSON `runtime/entrance_props_selection.json` é diagnóstico da seleção preparada pelo Server16, não uma regra editável.

O carregador Python e a DLL usam a mesma seleção direta. Para amistosos, `runtime/entrance_props_context.ini` transmite automaticamente `resolved_competition` com o ID atual, igual ao nome da pasta. Não é uma configuração editável ou distribuível. A DLL exige o mesmo processo FIFA, arquivo posterior à abertura do processo, os dois clubes atuais e ausência de competição/fase. A seleção é invalidada ao limpar o contexto e recalculada se o banco terminar de carregar depois da leitura dos times. Tabelas antigas de conversão, relatórios JSON e o TXT de referência não redirecionam os modelos.

As 251 pastas da base Honduras foram reorganizadas para os IDs atuais, preservando os 116 modelos disponíveis. A instalação anterior está em `ModCarrerMode/backups/entrance_direct_ids_20261018/competitions`. Os modelos continuam fora do Git. Ao instalar em outra máquina, substitua a pasta completa `competitions` pelo pacote atualizado; não mescle os números antigos com os atuais. O `FSW/settings.ini` do autor permanece sem alterações.

Os pacotes antigos com nomes, variantes não selecionadas, imagens e relatórios foram preservados em `ModCarrerMode/backups/entrance_ids_settings_20261014/competitions_original` em cada raiz. O mapa antigo fica nesse mesmo backup. Ferramentas e manifesto da migração ficam em `J:\mods\fifa 16\estudos fifa 16\42_ENTRADA_IDS_SETTINGS_20261014`.

Validação: testes Python de ID exato, fase sem herança, IDs autorizados pelo INI, corrupção, botão e continuidade dos outros recursos; testes de amistoso na mesma liga, ligas diferentes, copa com os mesmos clubes, banco atrasado, invalidação e correspondência única em compobj; testes nativos de seleção, apresentação e transparência, com contexto de outro processo, clubes diferentes e arquivo antigo recusados; compilação MSVC `/W4 /WX`. Reiniciar o FIFA e o Server16 carrega os executáveis e a DLL novos. A confirmação visual da abertura deve ser feita no jogo.

Revisão 21: ativação e recuperação do Lua no callback da cena, prontidão verificada, renovação dos recursos após troca de contexto e conclusão nativa de carregamento tardio após os cinco LODs. Consulte `../common/README.md` para o escopo, os testes e os limites da investigação de concorrência. O `settings.ini` original continua sendo a referência de IDs.
