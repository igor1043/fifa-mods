# Vestiário — acabamento de paredes 73

As faixas pintadas nas paredes usam grafismo geométrico limpo no lugar de pinceladas e riscos. A imagem base continua em 2048 × 512 com mipmaps completos; a escala de mapeamento passa a 240 × 60 cm por repetição, em vez de esticar a imagem inteira ao longo de cada parede. Isso preserva a proporção e a densidade de pixels tanto nas faixas horizontais como na área de hidratação.

A paleta continua dinâmica: cor secundária como fundo suavizado e cor primária nas faixas. A porção colorida é reduzida para 12% da área, com um friso discreto. Não há granulado ou manchas desenhadas. Os 40 murais personalizados permanecem intactos como painéis de destaque.

`interior_r73.rx3` recebe apenas coordenadas de textura novas no grupo graphic. Posições, índices, normais e demais grupos foram comparados à revisão 72. O nome de recurso novo evita que o cache do FIFA reutilize o modelo de mapeamento antigo. A montagem completa continua com 232 grupos no cenário do Criciúma.

Backup: `code-release/locker-room-wall-finish-r73-20261101/before-r73.zip`. O instalador e rollback da revisão permanecem nessa mesma pasta. Não há alteração de DLL, save, banco de dados, colisões ou câmeras. Sem commit ou push. A aparência dentro do FIFA ainda precisa de conferência após reabrir o jogo.
