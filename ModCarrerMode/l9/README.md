# Integração L9.65

O `dinput8.dll` da raiz continua sendo a entrada do pacote e abriga o código
de Career Mode deste repositório. Durante a compilação, o recurso
`ModCarrerMode/source/career_native/build/active_chain_resource.bin` é
incorporado à DLL. No primeiro uso, ele é materializado em
`dinput8_l9_chain.dll` na raiz do jogo e recebe as chamadas de DirectInput.

O recurso é o patch L9.65 importado do pacote suíço, SHA-256:

`B6583FC60B5058215B12E90E49E5F1D2A0B5069AA909EAB9B916621AD77AC6E2`.

O arquivo `dinput8_L9.ini` é deliberadamente externo: o L9 o lê na raiz do
jogo e ele permite ajustar as funções sem recompilar o núcleo. A configuração
integrada mantém os valores verificados no pacote de origem. As três opções
de diagnóstico/compatibilidade que lá estavam desligadas permanecem assim:

- `ScoutOhneLiga=0`;
- `Namensweiche=0`;
- `Poolwache=0`.

O `winmm.dll` é o CompData Patcher importado do mesmo pacote, SHA-256:

`B43513DDEAB5F9F0904EB76E4CB543596CA35B1AAAE3C60CE7993061B7AC1A0E`.

Ele é mantido na raiz porque o FIFA o carrega como proxy de WinMM. O módulo
escreve `compdata_patcher.log`; o L9 escreve `dinput8_L9.log`. A DLL antiga
`dinput8_career_chain.dll` é preservada no repositório como artefato de
recuperação, mas não participa da cadeia ativa desta branch.

Em uma execução real, confirme no `dinput8_L9.log` que os patches críticos
foram aplicados sem a mensagem
`NICHT weiterspielen`.
