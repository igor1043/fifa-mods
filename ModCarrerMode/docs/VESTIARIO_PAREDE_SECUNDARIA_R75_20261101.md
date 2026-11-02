# Parede secundária e ampliação longitudinal R75

Nova parede complementar com identidade dinâmica do clube, em geometria nativa:

- Mais 240 cm de comprimento, além dos 360 cm da R72: extensão total de 600 cm.
- Parede de 720 x 316 cm, com 69,90% da área na cor primária e 30,10% na secundária.
- Formas retangulares grandes, faixa horizontal e cores chapadas; sem gradientes,
  escudos, publicidade, quadros táticos ou LEDs decorativos nessa composição.
- Banco de 500 cm com estrutura primária, seis assentos secundários com bordas
  chanfradas, nichos inferiores, alguns equipamentos e armários nas extremidades.
- Luminárias convencionais adicionais no trecho novo, alinhadas à malha do teto.
- A parede principal, hidratação e 40 murais editáveis continuam disponíveis.

## Cores

Por padrão, usa as duas cores do clube selecionado. Sobrescritas opcionais em:

`ModCarrerMode/data/club_environment/room/secondary-wall.json`

```json
{
  "clubs": {
    "1043": {"primary": "#D00013", "secondary": "#101010"},
    "243": {"primary": "#FFFFFF", "secondary": "#B9A274"}
  }
}
```

O arquivo instalado traz apenas a sobrescrita branca/dourada do Real Madrid
(ID 243, conferido no catálogo local). Flamengo e Criciúma usam o próprio jogo.
As sobrescritas afetam a composição nova, sem editar o banco nem a carreira.
O monitor detecta alterações do arquivo e regenera os materiais. Preto absoluto
recebe refletância mínima no material para manter as bordas visíveis sob a luz.

## Integração e circulação

Malhas com caminhos R75 evitam reutilizar recursos R72/R74 em cache. O conjunto
de serviço é deslocado inteiro: portas, móveis, murais, placas, quadros, sombras,
bebedouro, limites, colisores e alvos das câmeras. Os armários dos jogadores
permanecem nas posições anteriores. O limite longitudinal nativo passa a 2305 cm.
O banco e os dois armários novos têm colisores de corpo próprios.

## Validação e rollback

Revisão local em `code-release/locker-room-secondary-wall-r75-20261101`:
`before-r75.zip`, instalador/rollback por arquivo, testes Python, testes nativos
da câmera e de circulação com os colisores reais, duas montagens completas e
prévias offline com as malhas/texturas finais. A avaliação visual dentro do FIFA
permanece pendente. Nenhum save foi modificado. Sem commit ou push.
