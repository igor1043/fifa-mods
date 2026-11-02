# Revisão local do modo carreira — 31/10/2026

## Mercado de técnicos

- Clique direto do mouse funciona por coordenadas do controlador, inclusive sobre as imagens dos cards. Hover conserva a seleção sem reconstruir os cards.
- L2/R2 alternam as abas principais e as abas do perfil. L1/R1 alteram o mês em Movimentações ou as páginas das listagens.
- Identidade do treinador reorganizada com retrato nas cores do clube, nacionalidade, clube, reputação, salário, situação, vínculo e confiança. Contrato mostra término e tempo restante.
- A visão geral apresenta campanha e últimos placares. A passagem por clubes tem métricas separadas e porcentagens formatadas com uma casa decimal.
- Os contratos existentes mantêm seus termos. Na renovação, campanha e capacidade financeira modulam a oferta salarial; o treinador pode recusar e ficar livre. O clube do usuário continua protegido contra decisões automáticas.
- A captura geral usa campanhas de todas as competições disponíveis; os contadores observados antes da demissão ficam no vínculo anterior. Jogos de um antecessor não são atribuídos ao sucessor.
- Auditoria do save de 10/08/2026: 175 competições, 77 ligas com tabelas, 1.549 clubes com jogos e 1.540 treinadores com campanha. Flick: seis jogos; Crespo: 11 no Al Ain; Pedro Morilla: 23 no Wuhan. Scolari não tem partida comprovada após chegar ao Al Ain em 30/07.

## Competições

- Textos rasterizados de acordo com resolução e zoom, com cache de texturas limitado e reaproveitado.
- Copas usam “Ver chaveamento”. Competições com grupos exibem os grupos, divisor e os mesmos cards do mata-mata no painel com rolagem.
- Analógico direito horizontal muda a fase. Vertical, roda do mouse e teclado rolam o conteúdo; o analógico esquerdo continua responsável por foco ou deslocamento no chaveamento ampliado.
- Barras de rolagem visíveis no painel e no chaveamento; ida, volta, agregado e destaques preservados.

## Novas opções dentro do jogo

- Escritório → carrossel de empregos → Outro clube. País/região, liga/divisão, clubes e chance de aceitação.
- Chance entre 5% e 90%, considerando diferença de prestígio e divisões; uma recusa bloqueia todos os destinos da mesma carreira durante 15 a 30 dias do calendário.
- Pedido aceito segue o contrato/proposta nativo do FIFA, com as mesmas validações do Server16. Não há edição direta do save para a transferência do treinador.
- Escritório → carrossel de opções → Aposentadoria. Dois cards: remover aposentadoria; remover e rejuvenescer para a idade configurada. Ambos exigem confirmação.
- Aposentadoria exige o save gravado no dia atual antes de confirmar e reutiliza o processamento existente: sair da carreira sem salvar novamente, esperar a aplicação com backup e reabrir somente após a confirmação.
- Pedidos vinculados à sessão/carreira e consumidos uma vez. Recusas armazenadas em tabela própria no sidecar `server16_loans.sqlite3`, separado do DATA nativo. A linhagem da carreira evita compartilhar o bloqueio com outra carreira.
- As funções correspondentes continuam no Server16 para comparação durante os testes do usuário.

## Validação

- 94 testes do mercado de técnicos; testes adicionais de propostas, catálogo e ponte das opções; navegação APT e geração idempotente dos carrosséis.
- Renderização real em D3D11 WARP das novas telas e do painel de competições, incluindo grupos e mata-mata; restauração do estado gráfico e cache limitado.
- Novo executável do Server16 com autoteste; os demais módulos do pacote foram preservados.
- Nenhum pedido de transferência, aposentadoria ou rejuvenescimento foi enviado à carreira do usuário durante os testes automatizados.
- A validação interativa com o controle físico dentro do FIFA fica para o teste do usuário. Tudo permanece local, sem commit nem push.
