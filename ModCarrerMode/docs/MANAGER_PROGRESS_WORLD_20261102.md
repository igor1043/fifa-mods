# Mercado e técnicos: progresso e regras globais — 02/11/2026

Revisão local, sem commit/push. Backup em
`code-release/manager_progress_20261102`.

## Progresso nativo

O mercado agora tem uma tela de progresso nativa APT, branca e dourada, com:

1. Consulta da carreira aberta.
2. Leitura de ligas e resultados.
3. Atualização de contratos e técnicos.
4. Organização dos perfis.
5. Preparação da tela e imagens.

A parte preenchida representa etapas realmente concluídas. O percentual é
explicitamente **das etapas**, não uma previsão de duração. Na revisão de
background, o tempo decorrido fica nos diagnósticos: o painel não é mais
recarregado a cada dez segundos apenas para atualizar um relógio.
O comando Voltar utiliza o evento de navegação e a legenda originais do FIFA.
Ao terminar, a tela dá lugar ao mercado; não fica com uma barra cosmética
avançando enquanto o trabalho está parado.

Um auxiliar isolado gera o painel de apenas ~6 KB, evitando disputar os
globais do compilador APT com a preparação pesada. Ele valida processo,
criação do processo, contexto, época, clube, data e recibo de leitura/gravação.
Um mutex de publicação impede que uma atualização de progresso sobrescreva
o mercado pronto ou uma carreira diferente. O auxiliar encerra quando termina
o processo de mercado que o iniciou.

## Carregamento do técnico 3D

- Prioriza uma animação nativa já preparada para o mesmo técnico, clube e
  recursos instalados, em vez de selecionar outra pose aleatória e refazer tudo.
- A extração original é reutilizada entre poses; geometria/texturas, ferramenta
  e identidade do clube entram na chave. Arquivos incompletos não são publicados.
- Perfil e modelo continuam separados. Uma preparação fria pode mostrar os
  dados antes do ator, usando o protocolo de identidade existente.
- `coach-timings.json` distingue leitura dos dados, extração, animação e cache.
- Não modifica a aparência, iluminação ou materiais para obter velocidade.
- Uma foto de técnico não equivale a um modelo 3D instalado. Nesta sessão,
  Felipão no Grêmio não tem entrada no registro de modelos; isso é exibido
  como indisponibilidade, sem substituir sua identidade pela de outro técnico.

## Países, ligas e movimentações

- Países, clubes e nacionalidades ordenados por chave normalizada, sem acentos
  deslocarem África/Áustria para o final ou Bélgica para depois de Brasil.
- Todas as divisões com clubes disponíveis continuam nos seletores; não há
  lista especial da Espanha nem filtro por países com movimentações.
- Movimentações abrem em **Todo o histórico**. O filtro mensal continua
  disponível, combinável com país e liga, evitando aparentes ausências causadas
  por uma seleção inicial apenas do último mês.
- A sessão verificada contém 102 ligas/divisões; as três divisões espanholas
  já existiam nos dados. Os registros anteriores tinham demissões em 19 países.

## Pressão e demissões

A política 6 aumenta a pressão de um aproveitamento confirmado abaixo da
expectativa de cada clube. Isso também vale quando a liga fornece somente
contadores/classificação agregados, sem os cinco placares individuais usados
no componente de forma recente.

- O peso do desvio de pontos por jogo é proporcional à expectativa relativa
  ao elenco de clubes da liga; um azarão pode tolerar uma campanha que é ruim
  para um favorito. A amostra cresce até oito jogos.
- Limiar padrão de pressão: 22; inclinação: 175 pontos-base por unidade;
  teto padrão: 5.500 pontos-base por avaliação. O ajuste regional brasileiro
  existente permanece. Valores personalizados são preservados na migração.
- Permanecem mínimos de tempo/jogos, intervalo de avaliação, limite anual de
  três demissões por clube, proteção do clube humano, compatibilidade de
  prestígio/salário na contratação e a raridade de recontratar um demitido.
- As novas regras valem nas próximas avaliações de evidência atual. Os eventos
  passados não são redistribuídos ou inventados para preencher meses vazios.

## Verificação local

- Tela de progresso executada na VM nativa, sem erros, com ajuda original e
  pacote menor que 20 KB. Testes de troca de época/data/clubes e reset da barra.
- Testes de países novos e três divisões por país sem IDs específicos.
- Testes de pressão de um favorito com 30% em países distintos e de tolerância
  maior para azarões; regressão de proteção do usuário e preservação do save.
- Teste do modelo preparado do Fluminense: 4,922 s, nenhuma chamada ao
  exportador, ator animado publicado no diretório de prova isolado.
- Na sessão de dezembro, a preparação completa observada passou de 177,743 s
  para 50,918 s; a barra registrou o avanço e terminou antes da publicação
  final. A comparação envolve caches e estado já preparado, não um prazo
  garantido para qualquer máquina ou novo recurso.
- O arquivo DATA do FIFA não foi alterado. A sessão não salva de dezembro foi
  mantida pelo handoff validado do mesmo branch.

Logs, hashes, teste completo e igualdade jogo/desenvolvimento ficam no backup
desta revisão. O teste visual de navegação no FIFA é feito pelo usuário.
