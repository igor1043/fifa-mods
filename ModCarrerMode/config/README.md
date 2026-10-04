# Configurações de FIFA Friends - New Experience

- `edition.ini`: identificação da edição, reaplicada pelo instalador.
- `career_native_mode.ini`: nível de diagnóstico.
- `career_retirement_background.ini`: fluxo legado por solicitação explícita, com espera pelo fechamento do FIFA.
- `career_retirement_background.ini.example`: referência de configuração, não é instalada.
- `career_retirement_background.local.ini`: diagnóstico privado opcional, ignorado pelo Git.
- `ranking_overlay.ini`: habilita o host das telas adicionais desta edição.

Torcida é configurada em `../crowd.ini` por compatibilidade do plugin compilado. O código nativo lê config/ e aceita os caminhos antigos como fallback; evite cópias divergentes. O instalador aplica a identificação e configuração de aposentadoria desta edição e preserva as demais configurações, salvo `-ReplaceConfiguration`.
