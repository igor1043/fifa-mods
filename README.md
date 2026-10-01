# FIFA 16 Mods

Pacote de modificações e ajustes para o FIFA 16, com foco no modo carreira.
Este README na raiz é a documentação central do repositório.

## Instalação

Instale somente os arquivos de execução, preservando a estrutura de pastas.
Não copie `source`, `tools`, `backups`, logs ou documentação para a instalação
do jogo. Antes de substituir arquivos, faça uma cópia externa em
`J:\mods\backup`; não guarde backups de tentativa dentro da pasta do FIFA.

O ponto de entrada é `dinput8.dll` na raiz do jogo. Ela incorpora o núcleo do
Career Mode e materializa `dinput8_l9_chain.dll` no primeiro uso. O arquivo
`dinput8_career_chain.dll` é mantido no repositório para recuperação e não
participa da cadeia ativa.

## Recursos do Career Mode

A DLL nativa reúne os recursos já implementados neste pacote, incluindo:

- cards e estatísticas de Meu Time, com mensagem de ausência somente em cards
  realmente vazios;
- separação dos dados de Liga e Copa na aba Competição;
- ranking mundial de clubes;
- card Próxima partida com data/hora, estádio, imagem, capacidade e público
  estimado quando os dados estão disponíveis;
- início da seleção de idioma com a bandeira do Brasil;
- fluxo de aposentadoria por idade, com alteração restrita ao banco necessário,
  validação de CRC/estrutura e restauração do arquivo se a validação falhar.

Os layouts e assets de interface ficam em `data/ui`; as bases de localização
ficam em `data/loc`. As imagens de reputação usam os IDs de liga 9900–9905,
com DDS em `data/ui/imgAssets/league/dark` e `league/light`.

## Plugins habilitados nesta branch

A lista efetiva está em `ModCarrerMode/mods/enabled.txt`:

- `crowd/crowd_plugin.dll` — ajuste do fator de público;
- `career_birthdate_2006/birthyear_range_2006_2012.dll` — faixa de ano no
  Player Career. A confirmação de persistência deve ser feita no jogo e após
  recarregar a carreira;
- `bench12_global_limit_12_v2/global_limit_12_v2.dll` — plugin legado
  relacionado ao limite do banco. Validar o resultado em uma partida antes de
  considerá-lo confirmado;
- `substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll`
  — localiza o par de regras da partida e grava o limite de sete trocas nos
  dois campos `A78C`. Não altera os contadores `B03C`; ainda é necessário
  confirmar da quarta à sétima substituição numa partida nova.

O `retirement_offline_worker.exe` é usado pelo fluxo de aposentadoria e
controlado por `ModCarrerMode/career_retirement_background.ini`. O plugin
`easfc_hide_plugin.dll` não está habilitado.

## L9.65 e logs

`dinput8_L9.ini` configura os patches L9.65 incorporados à DLL de entrada.
As opções `ScoutOhneLiga`, `Namensweiche` e `Poolwache` permanecem desligadas
(`0`). O recurso L9 importado tem SHA-256
`B6583FC60B5058215B12E90E49E5F1D2A0B5069AA909EAB9B916621AD77AC6E2`.
`winmm.dll` é o CompData Patcher e deve permanecer na raiz; seu SHA-256 é
`B43513DDEAB5F9F0904EB76E4CB543596CA35B1AAAE3C60CE7993061B7AC1A0E`.

Os principais logs são `dinput8_L9.log`, `compdata_patcher.log` e os arquivos
específicos em `ModCarrerMode/logs`. O modo de diagnóstico fica em
`ModCarrerMode/career_native_mode.ini`: `production`, `development` ou `trace`.
Feche e reabra o FIFA para a DLL reler essa configuração.

## Aposentadoria e segurança do save

O worker só atua após uma solicitação explícita armada por um dos fluxos
exclusivos de aposentadoria no Career Hub. Ele aguarda o FIFA liberar o par
`DATA`/`INDEX`, faz cópias de segurança, modifica somente o `DATA`, recalcula
os CRCs e valida novamente o container e a tabela `CZUM`. Se a validação
falhar, restaura automaticamente o `DATA` original. Arquivos auxiliares
pequenos não são tratados como o banco da carreira.

Os modos são `remove_retirement` (limpa `isretiring`, sem alterar idade) e
`remove_and_rejuvenate` (limpa `isretiring` e ajusta a idade, preservando mês
e dia). O worker não varre nem modifica saves sem solicitação pendente. Não
teste esse fluxo com a única cópia de um save importante.

## L9, nascimento e substituições: observações de validação

- O L9 escreve `dinput8_L9.log`; confira a aplicação dos patches críticos e
  não prossiga se aparecer `NICHT weiterspielen`.
- A DLL de nascimento e seus RVAs dependem do executável/build identificado.
  Nesta branch, confirme no jogo e recarregue a carreira para validar que o
  ano escolhido foi realmente salvo.
- A DLL de sete substituições não usa endereço absoluto de heap e rearma após
  os contadores reiniciarem ou o par de regras ficar inativo. Log de carga ou
  escrita, por si só, não comprova o funcionamento durante a partida.

## Traduções e arquivos de desenvolvimento

Os textos efetivamente carregados pelo FIFA estão nas bases `data/loc/*.db`.
Código-fonte, scripts de build e testes ficam em `ModCarrerMode/source` e não
são necessários para a execução do jogo.
