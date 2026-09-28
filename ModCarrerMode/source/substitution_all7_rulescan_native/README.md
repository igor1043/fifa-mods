# Substituições nativas: sete trocas

O plugin `substitution_all7_rulescan_native` é carregado pelo host existente do
FIFA 16. Ele busca o par de regras da partida pela vtable e pela distância
`0x458`, valida os campos e grava `7` nos dois limites `A78C`. Não grava nos
contadores `B03C` e não usa endereço absoluto de heap.

## Arquivos de execução no pacote

- `../../mods/substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll`:
  código do plugin.
- `../../mods/mod_host.dll`: carregador de plugins já utilizado pelo pacote.
- `../../mods/enabled.txt`: deve conter a linha
  `substitution_all7_rulescan_native\substitution_all7_rulescan_native.dll`
  sem `#` no início.
- Na raiz do pacote, `dinput8.dll` e `dinput8_career_chain.dll` são a cadeia
  de carregamento existente. Eles não foram recompilados para este plugin.

As DLLs de torcida, faixa de nascimento e banco de reservas também constam
no `enabled.txt` deste pacote. Seus binários estão nas respectivas pastas
`../../mods/`; são módulos independentes da regra de sete trocas.

## Código-fonte e compilação

O `.c`, o header e o `.cmd` desta pasta permitem recompilar a DLL x64 com
Visual Studio Build Tools. A compilação produz a DLL aqui; para atualizar o
pacote, copie-a para `../../mods/substitution_all7_rulescan_native/` com o
FIFA fechado. Arquivos `.obj`, `.lib` e `.exp` são intermediários de build.

## Validação

O teste manual em RAM confirmou a escrita pareada `A78C=7/7`. A DLL chegou a
registrar `pair_found` e `pair_write` no jogo, mas ainda é necessário
confirmar a 4ª até a 7ª troca em uma partida nova e o rearme em outra partida.
O log `ModCarrerMode/logs/substitution_all7_rulescan_native.log` é gerado no
jogo, não faz parte do pacote versionado.
