# Organização das abas da carreira — 29/10/2026

Reorganização local dos acessos existentes, a partir do XML instalado e funcionando.
Callbacks, IDs dos slides, providers dos olheiros e fluxos NAV foram preservados.

| Aba | Acessos |
|---|---|
| Central | Próxima partida e notícias no carrossel principal; avanço e treinamento preservados. |
| Elenco | Ferramentas esportivas nativas preservadas. |
| Meu time | Resumo completo do clube primeiro; Vestiário 3D como segunda página do carrossel inferior. As duas páginas aceitam foco para permitir a troca pelo controle. Estatísticas superiores preservadas. |
| Competição | Tabelas, grupos, chaveamentos e estatísticas já integrados, sem mudança. |
| Transferências | Carrossel grande: Mercado de transferências, Rede mundial, Mais caros, Mais recentes. Relatórios dos olheiros à direita com dimensões originais. Abaixo: carrossel de ações de jogadores e card próprio M. Técnicos. |
| Escritório | Carrossel financeiro: Finanças do clube, Empréstimos, Distribuir orçamento, Solicitar verba. Minha carreira ocupa o antigo espaço do vestiário. |
| Temporada | Calendário e Outras ligas permanecem na primeira linha. Ver clubes fica no antigo espaço de Estatísticas do time. No card inferior: Estatísticas dos jogadores e Estatísticas do time em carrossel. Notícias preservadas. |

O carrossel de ações de jogadores reúne Buscar jogador, Instruções do olheiro,
Escolhidos, Negociar jogadores e Negociações. Mantém os destinos, IDs, estados e
mensagens de indisponibilidade originais. Usa ícones existentes em vez das artes
altas que ultrapassariam o novo card compacto.

Na revisão seguinte, apenas a posição dos ícones do card grande de mercado foi
ajustada: o mesmo par DDS `ti_globaltransfernetwork_med_active/nonactive.dds`
passa ao topo, no tamanho original 292×204. Nenhuma imagem é substituída, editada
ou copiada. Os ícones dos cards compactos permanecem como estavam. O título do
card do técnico foi encurtado para `M. TÉCNICOS`, mantendo a fonte original.

O vestiário mantém seus fluxos de Cenas, Jogadores do time e Câmera livre. O
seletor global mantém 11 iniciais, Jogadores do time e Técnico do time. Não foram
criadas cópias desses fluxos nem alterados os menus internos.

## Arquivos

- `data/ui/layout/careermanagerhubcfg.xml`: layout ativo.
- `ModCarrerMode/source/native_mods/career_overlay/layout/careermanagerhubcfg.xml`:
  espelho completo do layout ativo, para futuras distribuições não restaurarem
  a organização antiga nem perderem as integrações mais recentes.
- `source/tools/reorganize_career_hub.py`: transformação pura, idempotente e com
  validações de geometria, contagens e destinos. Recebe o layout de origem e uma
  saída diferente, para que a instalação seja uma etapa separada.
- `source/tests/test_career_hub_reorganization.py`: regressão sobre o layout que
  estava funcionando antes da mudança.

Nenhum arquivo de save, SQLite, idioma, NAV, APT/BIG ou DLL é modificado pela
reorganização. O XML usa os carrosséis e a navegação nativa já instalados, com
teclado e controle. A confirmação visual dentro do jogo continua necessária.

## Backup e rollback

O backup desta instalação fica no desenvolvimento, em
`code-release/career_hub_reorganization_<data>_<hora>/` e, para o refinamento seguinte, em `code-release/career_hub_refinement_<data>_<hora>/`. O arquivo `before.json`
lista individualmente os arquivos anteriores do jogo e do desenvolvimento;
`installed.json` registra os hashes instalados. As versões anteriores dos dois
XMLs eram diferentes e são restauradas individualmente, sem misturar as bases.

Use `Restaurar-Cards.ps1` dessa pasta com FIFA fechado. Ele confere os hashes do
backup e recusa sobrescrever alterações posteriores inesperadas. Restaura apenas
os arquivos desta revisão; não faz reset do Git nem rollback dos demais mods.

O FIFA lê o layout ao iniciar a carreira. Se já estiver aberto durante uma
instalação, reinicie o jogo para carregar a nova organização.
