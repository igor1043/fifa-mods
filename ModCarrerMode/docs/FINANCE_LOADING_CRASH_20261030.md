# Finanças: falha ao abrir a tela — 30/10/2026

O FIFA mantinha uma janela modal `Game crash` aberta. Por isso o processo ainda
respondia às consultas do Windows, embora a interface estivesse interrompida.
O diagnóstico correto está no `crash.dmp` gerado pelo jogo.

O dump da sessão 29576 registra acesso inválido em `fifa16.exe+0x3A82624`, na
iteração da lista nativa de objetos que recebem entrada. A configuração lida
em RAM identifica `AptInitParmsT::iButtonSetSize = 512`; a falha acontece no
índice 512, o 513º objeto. O pacote financeiro da carreira tinha 43 páginas e
508 botões com callbacks registrados de uma vez, inclusive páginas ocultas.
Além disso, a saída da tela não desfazia os callbacks nem a referência ao dono
do botão, permitindo que controles antigos sobrevivessem a uma recarga.

`finance_ui.py` agora registra somente os botões da página visível, remove os
callbacks e a referência `owner` antes de trocar de página e faz a mesma limpeza
na saída. A seleção e os valores também são atualizados somente na página ativa.
Nenhum limite ou código da engine é alterado.

No pacote gerado com a publicação da carreira: 508 controles de páginas no
arquivo, 13 registrados na abertura, no máximo 16 por página e zero ao sair.
A inicialização passou de 28.038 para 2.772 instruções no verificador APT.
Os 29 testes direcionados de interface, moeda, receitas, switches e ponte
financeira passaram, incluindo histórico de 80 jogos que gera mais de 512
controles no pacote e duas recargas com liberação dos objetos anteriores.

Dump, pacote anterior, pacote corrigido e relatório estão em
`code-release/finance_loading_crash_20261030/`. A instalação permanece local,
com backup e manifesto. DATA, INDEX, banco de técnicos e empréstimos não são
editados pela correção da interface.
