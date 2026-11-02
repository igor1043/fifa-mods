# Revisão local do mercado de técnicos — 02/11/2026

## Identidade e estatísticas

- Corrigida a importação de `career_profile` quando o leitor de clubes executa
  `manager_market` como pacote. O teste usa um processo novo, sem acrescentar
  artificialmente a pasta interna do mercado ao caminho de módulos.
- O leitor aguarda o vínculo da carreira atual antes de publicar a identidade;
  não mostra o técnico padrão do catálogo enquanto o mercado está pendente.
- Passagens e histórico anual têm abas distintas. Um resumo anual não representa
  outra contratação. Renovações explícitas continuam unidas à mesma passagem.
- Com a campanha completa e datada disponível, um técnico contratado depois
  recebe somente os jogos atribuídos ao seu vínculo. Um contador antigo anterior
  à contratação não pode ser usado como se fosse a leitura do dia da posse.
- A simulação processa somente os novos jogos do respectivo dia, preservando a
  ordem cronológica sem percorrer de novo toda a lista a cada data.

Na cópia de auditoria desta sessão, Felipão tem uma passagem no Grêmio e 32
jogos. Tite tem duas passagens no Botafogo: saiu em março, Dunga foi contratado,
Dunga saiu em novembro e Tite retornou. A passagem atual de Tite contém 5 jogos.
Esses eventos já registrados foram preservados.

## Mercado e navegação

- Chance de demissão sob pressão aumentada: limiar 26, inclinação 125 pontos-base,
  teto de 40% por avaliação elegível. Permanecem tempo mínimo, jogos mínimos,
  intervalo entre avaliações, limite anual e proteção do clube do usuário.
- Recontratação de técnico demitido pelo mesmo clube: elegibilidade rara de 1%
  antes de 180 dias e 5% depois. Ainda precisa passar por qualidade, salário,
  disponibilidade e seleção. A decisão é reproduzível por vaga/data, sem repetir
  o sorteio ao abrir a tela. Não muda movimentos que já aconteceram.
- Filtro de movimentações por liga, com país e competição identificados.
- Dots dos clubes clicáveis; barras de movimentações e histórico aceitam clique
  na trilha e arraste pelo mouse, além da navegação existente de controle/teclado.

## Carregamento

Um vínculo novo não altera mais o fundo da miniface nem a lista de imagens de
cada seção. Os retratos continuam sendo os arquivos instalados; o painel usa um
fundo neutro estável. Assim a geometria e as texturas podem ser reaproveitadas
quando os técnicos mudam de clube.

Os currículos são dados compactos na APT; apenas o selecionado é decodificado.
O pacote completo foi validado com 1.992 pessoas, carregamento em 19 quadros de
inicialização e zero erros no interpretador de navegação. A reconstrução com o
template preparado ficou em aproximadamente 13 segundos nesta máquina, contra
cerca de 60 segundos no registro anterior. A geração continua em background;
esses números não são uma promessa de latência idêntica em outro computador.

## Segurança da atualização

Revisão local, sem commit/push. Backup em
`code-release/manager_revision_20261102_115604/`, incluindo o banco do mod,
os scripts anteriores e o hash do save nativo. A instalação reinicia somente os
leitores auxiliares e usa handoff validado da sessão para preservar o ramo da
carreira ainda não salva. DATA/INDEX e tabelas nativas do FIFA não são alterados.
