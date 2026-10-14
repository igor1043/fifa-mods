# Revisão 18 — abertura e transparência dos escudos

Corrige a permanência dos objetos quando a apresentação é avançada com A e o fundo azul dos escudos, inclusive os colocados no gramado na Libertadores.

## Visibilidade

O fechamento da segunda escalação continua sendo a retirada normal. Quando a abertura é pulada, o encerramento da tarefa nativa `IntroScriptAssignment` ou a câmera nativa de jogo na fase 0, ainda em 0:00, encerra a apresentação sem depender dos eventos das escalações. A ausência temporária de serviços, o áudio do hino, uma pausa ou um replay não bastam para retirar o conjunto. A retirada fica registrada até uma nova abertura de partida.

Não intercepta o botão A: observa o resultado nativo do avanço. Isso permite avançar uma cena intermediária e continuar exibindo os objetos quando a apresentação ainda prossegue. A regra não consulta a arte do placar nem a aparência da escalação.

## Escudos

Cada partida consulta os IDs do mandante e visitante e os DDS em `data/ui/imgAssets/crest/light/l<ID>.dds`. O atlas preserva o alfa original, sem compor o fundo azul. As superfícies dos emblemas são recortadas pelo contorno do alfa, inclusive seus espaços vazios. Esse recorte também funciona com o material estático já aprovado no FIFA. A cor recebe margem nas bordas transparentes para evitar contornos escuros por filtragem.

A estrutura, placas e emblemas continuam em uma única malha e no mesmo ator. Compartilham posição, rotação, caixa de renderização e retirada. A geometria original da estrutura e as texturas de normal e coeficientes são preservadas.

O cache novo fica em `data/sceneassets/entrance_props/competitions/<conjunto>/fixtures/alpha18_<clubes>_<hashes>/`, com `model.rx3` e `textures.rx3`. É separado dos atlas opacos anteriores. Cada arquivo gerado passa pelo validador nativo antes de ser publicado ao carregador. Um escudo ausente ou inválido deixa apenas suas superfícies de emblema vazias. Uma falha de geração impede solicitar aquele recurso. Uma competição sem pacote continua sem objetos.

## Instalação e testes

DLL: `ModCarrerMode/mods/entrance_props/entrance_props.dll`. A lista `mods/enabled.txt` deve ter uma única revisão deste mod, antes de `var_cabin`. A integração Lua e o executável Server16 da revisão 17 são mantidos. Não é necessário um novo build do CR16/Server16 para esta correção.

Feche e abra novamente o FIFA. Reiniciar apenas a partida não troca a DLL já carregada. Para conferir, teste a abertura completa e depois outra partida avançando com A; o conjunto e os emblemas devem sair juntos. O log `ModCarrerMode/logs/entrance_props.log` identifica `scene v18` e o motivo da retirada.

Validação fora do jogo: compilação MSVC `/W4 /WX`; regressões de escalações, pausas, hinos, reinício e avanço; codificação BC3 alfa; recorte com buracos; conversão IEEE half; escudo ausente e malha corrompida; 147 pacotes e 106 conjuntos com superfícies de escudo. Série A e duas variantes da Libertadores também foram lidas por um parser independente e renderizadas no Blender. A transparência exportada corresponde aos DDS, a geometria original da estrutura permanece e nenhum triângulo gerado cobre o fundo vazio dos emblemas desses três casos.

Os renders em `previews/` mostram os RX3 gerados, com material opaco, e não capturas do FIFA. A execução desta revisão no jogo ainda precisa ser confirmada pelo usuário. Na sessão usada para estudar o avanço, a leitura externa da RAM foi recusada pelo Windows; a evidência veio do log da revisão 17, com câmera `bc: broadcast pos`, fase 0, relógio 0 e nenhuma escalação concluída.

Para reproduzir na instalação local, execute `build.cmd`. Os testes básicos não precisam de uma instalação do FIFA. Para testar pacotes locais, execute `build/competition_catalog_test.exe "PASTA_DO_FIFA" --all-mesh`. Os scripts e renders históricos permanecem na pasta externa de estudos. O instalador do pacote em `ModCarrerMode/tools/maintenance/Install-Game.ps1` preserva os demais recursos locais.
