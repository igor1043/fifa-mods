# Estrelas de reputação

A aba de reputação usa `MYTEAM_CLUB_PRESTIGE` como asset de liga. O código
nativo fornece IDs 9900–9905, conforme a quantidade de estrelas, e o resolvedor
da interface carrega `league/dark/l<ID>.dds` ou `league/light/l<ID>.dds`.
As 12 imagens correspondentes precisam acompanhar o layout e a DLL nativa.

Os três DDS em `tiles/careerhub/reputation_*` também foram preservados do
pacote instalado, mas os assets por ID em `league/` são os referenciados pelo
campo atual da tela. Não são necessários scripts ou serviços externos para
exibir essas imagens.
