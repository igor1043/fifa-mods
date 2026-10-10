# Banco de 12 reservas â€” versÃ£o 8

MantÃ©m os 12 reservas e os sete modelos originais de cada banco. Os cinco modelos adicionais de cada equipe ficam ocultos enquanto estÃ£o fora de campo; o setter nativo de atividade libera o modelo quando ele entra por substituiÃ§Ã£o.

A versÃ£o 7 do commit 3ff1829 continua presente na branch e era a DLL instalada (SHA256 B3492EA95B3EEEFA88B788BE2EE4E25AAB56D09EAE1995B5A28103ECA5F953CB). Na sessÃ£o de 10/10/2026, o banco carregou mas todos os extras ficaram com polÃ­tica de visibilidade 2 e flags nativas 0x9, sem ocultaÃ§Ã£o; a saÃ­da moderna v5 recusou instalar por destino de chamada ainda nÃ£o preparado. Portanto, os extras visÃ­veis naquela sessÃ£o nÃ£o dependiam de uma alteraÃ§Ã£o instalada pela saÃ­da moderna.

A versÃ£o 8 cobre o modelo que chega Ã  abertura sem classificaÃ§Ã£o como extra: depois do carregamento, no Show ou numa atualizaÃ§Ã£o de inatividade, cruza o ID/side da tabela RNA com o elenco, o papel 28 e o bit nativo de inatividade 0x8. Classifica somente os cinco IDs adicionais. MantÃ©m as travas anteriores de ativaÃ§Ã£o para nÃ£o voltar a ocultar um adicional jÃ¡ substituÃ­do. NÃ£o altera assentos, coordenadas ou papÃ©is dos atletas.

ValidaÃ§Ã£o automatizada: build_bench_native12.cmd passa as verificaÃ§Ãµes de assinaturas, importaÃ§Ã£o, papÃ©is 7/12, fila/ABI/unwind/rollback e renderizaÃ§Ã£o. Os testes novos cobrem Show sem descritor de banco, flag de banco ausente no carregamento e liberaÃ§Ã£o posterior pelo setter nativo real. ValidaÃ§Ã£o visual da abertura com a saÃ­da moderna v6 ainda pendente.

SHA256 da DLL v8: D4A0BC767188D1597686AF77ACC988ABC80F8EB96C032339BF519F57B5903460.

ValidaÃ§Ã£o em partida em 10/10/2026: o usuÃ¡rio confirmou que a abertura, a saÃ­da de bola moderna e a substituiÃ§Ã£o funcionaram juntas. A captura `bench_v8_opening_hidden.json` registra os dez extras com flags 0x1B e os elencos com 12 reservas por equipe; os logs registram os dois plugins instalados apÃ³s reiniciar. O hash final do banco permanece D4A0BC767188D1597686AF77ACC988ABC80F8EB96C032339BF519F57B5903460.
