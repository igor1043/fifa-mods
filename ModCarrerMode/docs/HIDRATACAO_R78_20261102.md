# Hidratação do vestiário — revisão local R78

## Arte por clube

Arquivo: `ModCarrerMode/data/club_environment/room/clubs/<ID>/hydration.png`.

O Flamengo (1043) usa a imagem exata fornecida pelo usuário em 02/11/2026,
2172 × 724 px, sem alterações no PNG de origem. A superfície mede 500 ×
166,67 cm (3:1). A conversão nativa gera mipmaps e mantém a imagem inteira;
outras proporções recebem margens em vez de cortes ou deformação.

Sem arquivo próprio, o clube recebe fundo branco e título/escudo nas cores
do clube. Não reutiliza a arte do Flamengo para outras equipes. Alterar o
PNG muda o hash acompanhado pelo serviço da sala.

## Móveis

Bancada com seis portas, puxadores, rodapé e tampo; prateleira com toalhas,
recipientes e maleta; dois recipientes térmicos laranja, copos empilhados,
bandeja com frutas e seis squeezes com identidade do clube. Refrigerador
com três prateleiras e dezoito garrafas de água/reposição/energético.

A abertura frontal da geladeira não usa uma grande superfície transparente
que possa ocultar os próprios produtos por escrita de profundidade. Moldura,
puxador e duas faixas estreitas sugerem o vidro. As novas superfícies curvas
possuem orientação das faces voltada para fora.

As cores dos líquidos, frutas, aço, toalhas e recipientes térmicos preservam
o contraste natural. O bebedouro CC0 existente foi reposicionado junto à
extremidade esquerda. Não foram adicionados modelos externos novos.

## Instalação e recuperação

Revisão somente de modelos, arte e scripts da sala; não altera DLL, save,
banco de dados, finanças, câmera ou escala de iluminação da engine.

Pacote revisável: `code-release/hydration-r78-20261102`.
`before-r78.zip` guarda os arquivos anteriores das duas instalações.
`rollback.py` verifica hashes antes de restaurar, preservando mudanças
posteriores que conflitem. Reiniciar somente o serviço da sala após instalar
ou restaurar permite recarregar os scripts com FIFA aberto. Sair e voltar ao
vestiário também atualiza a visualização.

## Verificação

Oito testes de arte/proporção, fallback, geometria, orientação de faces,
preservação de triângulos externos, geladeira e colisões. Montagem nativa
isolada para Flamengo e Criciúma, sem escrever no save nem anexar ao jogo.
Prévia offline com os modelos e texturas reais; a iluminação dessa prévia
não substitui uma confirmação visual dentro do FIFA.
