> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Protocolo compartilhado — execução em 07/10/2026

## Entrega

`src/tetris_shared/protocol.py` implementa `encode`, `parse` e `Framer.feed`.
Oito tipos TVP/1, campos estritos, ASCII, LF obrigatório e limite por linha
estão cobertos por testes. Framer conserva fragmentos por instância, não
copia lotes excessivos para seu buffer e permanece inválido após excesso.
A API pública mantém os nomes previstos; parâmetros, auxiliares e variáveis
novos usam português. Não foram adicionados comentários ao código.

A implementação valida sintaxe. Validar direção, fase e combinações semânticas
de resultado/motivo é trabalho dos adaptadores. Por exemplo, a gramática pode
representar CANCEL/KO, mas o controlador deve rejeitar essa combinação pela
política de resultado. O protocolo compartilhado não possui estado da partida.

O usuário confirmou a interface pronta e autorizou explicitamente esta etapa.
A restrição histórica de stubs foi atualizada em AGENTS.md somente para o
protocolo compartilhado. Métodos de transporte continuam como TODO[EP-REDE].

## Evidência

- Antes da implementação: 18 testes de protocolo executados; falhas por
  `NotImplementedError` nos três pontos antigos. Log local em
  `/tmp/tetris-protocolo-red.log`.
- Depois: 18 testes de protocolo aprovados, com exemplos literais de todos os
  tipos, ASCII inválido, campos ausentes/extras, limites, fragmentação byte a
  byte, todos os pontos de divisão do fluxo e isolamento por conexão.
- O teste de fronteira em `tests/test_client.py` passou a exigir stubs apenas
  do transporte; continua verificando ausência de thread e de fallback fake.
- Suíte completa: 97 testes aprovados, incluindo os oito testes PTY do milestone 1.
- Nenhum socket foi implementado; motor, thread/filas e temporizadores preservados.

Comandos:

```bash
PYTHONPATH=src python3 -m unittest tests.test_protocol -v
PYTHONPATH=src python3 -m unittest discover -s tests
git diff --check
```

## Próxima etapa

Implementar o controlador de partida única do servidor e sua máquina de
estados, seguido do transporte TCP e integração no cliente. O protocolo já
pode ser reutilizado por ambos; usar uma instância de Framer por conexão.
Nenhum arquivo foi adicionado ao staging, commitado ou publicado nesta etapa.
