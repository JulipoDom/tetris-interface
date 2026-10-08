> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Integração TCP TVP/1 Implementation Plan

> **For agentic workers:** Use test-driven development for each behavior and a reviewer outside its implementation front. Track the integration against `docs/STATUS_TCP.md`.

**Goal:** Executar partidas TCP sequenciais entre dois clientes curses e o servidor, com resultado coerente e falhas delimitadas.

**Architecture:** Manter o codec TVP/1 comum em duas cópias idênticas, um dispatcher sequencial para o domínio do servidor e uma thread de rede por cliente que publica eventos para a thread principal da TUI. Usar sockets TCP da biblioteca padrão, com framing, buffers limitados e relógio monotônico. Uma rodada termina antes de admitir a dupla seguinte.

**Tech Stack:** Python 3.12+, biblioteca padrão, `unittest`, `curses`.

**Spec:** `docs/PROTOCOLO_TCP.md` e `../tetris-server/00-contexto-geral.md`.

## Global Constraints

- Oito tipos TVP/1; ASCII; LF; 512 bytes por frame, 4096 bytes de saída por conexão.
- Dois jogadores e uma partida ativa, com rodadas sequenciais no mesmo servidor.
- HELLO em 5 s, KEEPALIVE a cada 5 s, inatividade em 15 s, drenagem final por até 1 s.
- Sem frameworks ou dependências novas; preservar treino e simulação.
- Estilo: aplicar somente padrões comprovados em `docs/ESTILO_AUTOR.md`.

## Review Focus

- Fragmento de 511 bytes seguido de LF deve ser aceito; 512 sem LF deve falhar.
- Terceiro cliente não afeta a partida já admitida.
- KO e desconexão próximos não substituem o primeiro resultado gravado.
- Um cliente lento não cresce fila sem limite nem atrasa o outro indefinidamente.
- Fechar a TUI durante conexão/espera libera sua thread e socket.

## Tarefas e donos dos arquivos

1. **Contrato, estilo e codec (orquestrador + agente histórico).** Arquivos: `docs/PROTOCOLO_TCP.md`, `docs/STATUS_TCP.md`, `docs/ESTILO_AUTOR.md`, `tetris-server/src/tetris_shared/protocol.py`, `tetris-server/tests/test_protocol.py`. Confirmar cópias idênticas e testes de protocolo.
2. **Servidor e partida (agente servidor).** Arquivos exclusivos: `tetris-server/src/tetris_server/network.py`, `tetris-server/src/tetris_server/__main__.py`, testes de servidor e integração no repositório servidor. Adaptar eventos tipados a TVP/1, aceitar duas conexões, rejeitar terceira, validar prazos/fases, drenar GAMEOVER, limpar rodada e reiniciar admissão. Usar `MatchController` existente como autoridade.
3. **Cliente e TUI (agente cliente).** Arquivos exclusivos: `tetris-interface/src/tetris_client/network.py`, `app.py`, `ui.py`, `__main__.py`, testes correspondentes. Iniciar sem bloquear, serializar envios, validar mensagens por fase, publicar eventos tipados e encerrar thread/socket; manter treino/simulação.
4. **Integração e revisão (orquestrador + revisor independente).** Verificar protocolo idêntico, testar codec, domínio e TUI; testar duas conexões reais quando o ambiente permitir. Reproduzir e corrigir falhas relevantes com teste antes da correção; atualizar README, `00-contexto-geral.md` e `STATUS_TCP.md` com estado efetivo. Registrar claramente testes impedidos pelo sandbox.

## Verificação

Executar `PYTHONPATH=src python3 -m unittest discover -s tests` em cada repositório. Testes TCP reais devem abrir sockets de loopback com prazos explícitos; quando `socket.socket()` for proibido, registrar a restrição e não contar os testes ignorados como validação. Executar `git diff --check`, conferir estado local e confrontar a implementação com o contrato e o guia de estilo.

## Continuação da missão em 08/10/2026

- Agente histórico: somente leitura das fontes e evidências; orquestrador atualiza os dois guias de estilo.
- Revisor do servidor: somente leitura de domínio, transporte e testes; orquestrador corrige defeitos com regressões em `tetris-server/src/tetris_server/app.py`, `network.py` e testes correspondentes.
- Agente de integração: responsável exclusivo pelo novo `tetris-interface/tests/test_tcp_integration.py`. Usar o servidor irmão em subprocesso com seu próprio `PYTHONPATH` e dois clientes `App`/`NetworkSession`, sem substituir o transporte. Cobrir duas partidas sequenciais, tabuleiros, ataques, derrota do motor, resultado e liberação das threads; registrar skip quando sockets forem proibidos.
- Orquestrador: responsável exclusivo pelos documentos compartilhados e READMEs; executar as suítes e solicitar revisão independente das correções e do novo teste integrado.

Regressões do servidor: prontidões repetidas não permitem crescimento ilimitado dos registros; rajada de conexões devolve controle ao dispatcher em até 32 tentativas; parada solicitada impede novas admissões. A política preserva decisões e mensagens da partida.
