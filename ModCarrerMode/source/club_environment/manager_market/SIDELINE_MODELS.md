# Técnicos à beira do campo por carreira — análise

## Ponto de integração confirmado

O jogo monta os técnicos mandante/visitante pelos tipos SLC 10 e 11 em
`data/fifarna/lua/assets/sle.lua`. `SleUpdate` identifica o clube por
`homeKitTeamID`/`awayKitTeamID`. `GetRMSle(idx, isModel)` monta uma lista de
arquivos `specificmanager_<clube>_<competição>_<variante>.rx3` e seus pares de
textura. `GetTexture` já utiliza esse resolvedor para o técnico.

O exportador da tela de técnicos usa atualmente o par original
`data/sceneassets/slc/specificmanager_<clube>_0_0{,_textures}.rx3`.
As contratações do mercado alteram a identidade e as estatísticas na base
auxiliar, mas ainda não redirecionam esse par na partida. Miniface e modelo
3D são catálogos diferentes.

## Implementação proposta

1. Cadastrar `coach_id → modelo RX3 + texturas + rig/LODs compatíveis` em uma
   tabela de modelos do catálogo do mod. A identidade do técnico permanece
   estável ao trocar de clube. Os arquivos originais dos clubes permanecem
   intactos; nenhuma cópia deve sobrescrever `specificmanager_<clube>`.
2. O serviço de mercado publica um mapa pequeno dos vínculos ativos após o
   commit da simulação, junto com PID, criação do processo, contexto, epoch,
   carreira, data e revisão do checkpoint. O renderizador consome somente esse
   mapa validado; não consulta SQLite durante o desenho.
3. No início da partida, um wrapper de `GetRMSle` consulta o clube dos dois
   atores de técnico. Se houver vínculo daquela carreira e modelo cadastrado,
   resolve modelo e textura do técnico contratado. Os demais tipos SLC seguem
   o resolvedor original. O recurso entra pelo carregador e animação do FIFA.
4. A troca entra antes do carregamento do ator da próxima partida. Uma
   contratação não provoca reescrita ou recriação por quadro. Uma alteração
   durante recursos já carregados exige o ciclo nativo de descarregar/religar
   validado, em vez de trocar ponteiros enquanto o ator está sendo desenhado.
5. Ao sair da carreira ou carregar outro save, o mapa é descartado e a nova
   revisão precisa ser validada. Em amistoso, nova carreira ou contexto não
   confirmado, o resolvedor original permanece ativo.

## Ausência de modelo

Uma foto não permite recuperar automaticamente uma face 3D. Um técnico sem
modelo instalado pode usar um técnico genérico do FIFA, com a limitação
indicada no perfil. Não deve herdar a face do técnico demitido. Modelo,
textura, rig e LODs precisam ser verificados como um conjunto; a roupa de um
modelo específico também pode exigir adaptação às cores do novo clube.

## Validações antes de habilitar

- Duas carreiras com técnicos diferentes no mesmo clube; recarregar um save
  anterior deve restaurar seu vínculo, modelo e data.
- Novo modo carreira e amistoso devem usar os modelos padrão.
- Contratações mandante/visitante, ida/volta à Central e segunda partida na
  mesma sessão, sem herdar recursos da cena anterior.
- Modelo ausente, textura ausente e rig incompatível devem usar fallback
  definido, sem publicar o conjunto incompleto.

Esta revisão implementa as melhorias de mercado e carregamento. O
redirecionamento dos atores SLC acima continua como próximo desenvolvimento,
conforme o pedido de análise, sem modificar a partida atual.
