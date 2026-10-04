# Configurações

- `career_native_mode.ini`: nível de diagnóstico da carreira.
- `ranking_overlay.ini`: opções do ranking.
- `career_retirement_background.ini`: regras do worker legado de aposentadoria.
- `career_retirement_background.ini.example`: exemplo, não executado.
- `career_retirement_background.local.ini`: opcional, configuração privada de diagnóstico; não versionar.

**A configuração de torcida continua em `../crowd.ini`.** O plugin de torcida já compilado exige esse caminho; ele foi preservado por compatibilidade.

O código nativo lê primeiro `config/` e aceita os caminhos antigos como fallback. Não crie cópias divergentes do mesmo arquivo nos dois lugares.
