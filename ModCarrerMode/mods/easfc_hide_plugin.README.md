# Ocultação EASFC

`easfc_hide_plugin.dll` é um plugin opcional para `mod_host.dll`. Ele oculta o
widget/banner de reconexão EASFC na interface; não altera a IA das partidas.

O plugin está temporariamente desabilitado em `enabled.txt`: os dumps de
26/09/2026 registraram repetidamente `0xC0000005` em
`easfc_hide_plugin.dll+0x17660`. O arquivo permanece no pacote para uma futura
versão corrigida. O log da instalação de origem registrou
`patched EASFC reconnect widget` e `EASFC banner hidden` em 22/09/2026.

Não foi encontrado código-fonte ou configuração adicional desse plugin na
instalação. O arquivo de log é gerado em execução e não integra o pacote.
