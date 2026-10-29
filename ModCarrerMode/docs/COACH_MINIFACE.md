# Miniface em Técnico do time

A tela usa o mesmo arquivo PNG já instalado em
`ModCarrerMode/data/manager_market/minifaces` para o treinador atual.
O campo `portrait` acompanha a identidade no perfil `coach.tsv`.

O vínculo atual do mercado de técnicos tem prioridade. Se esse vínculo ainda
não estiver disponível, o nome do save é comparado com o catálogo em modo de
somente leitura. Identidade ambígua ou foto ausente usa a imagem genérica;
nunca mantém a miniface do técnico anterior. Não se cria cópia das fotos.

A imagem fica no card de identidade, ao lado do nome e da nacionalidade.
Mantém proporção e transparência e usa a mesma carga PNG/cache gráfico que
os outros elementos da tela. O modelo 3D permanece independente: a foto pode
aparecer mesmo quando o modelo do treinador não estiver instalado.

A revisão não altera dados do mercado, contratos, saves, animação, iluminação,
buffer do ator ou pipeline de renderização. Precisa reiniciar o FIFA para
carregar a DLL com o novo elemento visual. Alterações mantidas localmente.
