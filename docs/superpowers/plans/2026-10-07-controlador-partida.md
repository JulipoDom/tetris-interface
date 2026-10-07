# Controlador da partida única — plano de implementação

> Execução sequencial com as skills executing-plans, test-driven-development e verification-before-completion. Sem agentes, worktrees ou commits adicionais.

**Objetivo:** implementar a máquina de estados da única partida, pronta para receber eventos do futuro transporte.
**Arquitetura:** pacote tetris_server com controlador puro e ações imutáveis. Entradas usam uma referência opaca hashable por conexão; nenhuma identidade ou mensagem nova trafega no protocolo. Uma instância é conduzida sequencialmente pelo futuro loop do servidor.
**Tecnologia:** Python 3.12+, dataclasses, enum, unittest e protocolo compartilhado existente.
**Especificação:** 00-contexto-geral.md, seções 5–8, e IMPLEMENTATION.md.

## Restrições

Dois jogadores, uma partida, oito mensagens. Sem sockets, timers, física, curses, CLI de servidor ou novas dependências. Identificadores novos em português; sem comentários no código. Preservar as alterações anteriores na branch atual.

## Interfaces e decisões

Arquivo novo: `src/tetris_server/partida.py`; pacote: `src/tetris_server/__init__.py`.

- `ControladorPartida.admitir(conexao)` retorna ações; a terceira conexão recebe FecharConexao. Referência já admitida é erro de chamada, não um terceiro jogador.
- `receber(conexao, tipo_mensagem, campos)` recebe os tipos do protocolo compartilhado. Sintaxe e direção/fase inválidas tornam-se falha PROTOCOL. Não processa bytes de TCP.
- `desconectar(conexao)` e `falhar(conexao, motivo)` recebem falhas observadas pelo adaptador. Motivos aceitos em falhar: DISCONNECT, TIMEOUT e PROTOCOL; erro de parser/framing também usa PROTOCOL.
- `parar()` produz CANCEL/SERVER_STOP e encerra mesmo sem participantes.
- Fases: AGUARDANDO, PREPARACAO, ATIVA, ENCERRADA. Propriedades fase e decisao para consulta; decisão imutável com resultado por conexão identificada.
- Ações: EnviarMensagem(conexao, tipo_mensagem, campos) e FecharConexao(conexao), congeladas. Não adicionam tipos TVP/1.
- Após HELLO válido, participante não pode ser substituído. Antes dele, falha libera a posição sem cancelar o outro jogador.
- Ao falhar um identificado, marcar a conexão indisponível, gravar a decisão e notificar apenas identificados disponíveis. Resultado do ausente fica registrado internamente.
- GAMEOVER precede o encerramento físico dos clientes alcançáveis: transporte futuro deve escoar por até um segundo e fechar. O controlador só fecha imediatamente rejeitados/infratores e candidatos anônimos ao terminar.
- Depois da decisão, entradas tardias não geram encaminhamentos nem outra decisão. Novas conexões são rejeitadas. Callbacks de referências desconhecidas são ignorados como eventos atrasados.
- READY/PLAYER repetido na preparação e atrasado no jogo é idempotente. KEEPALIVE após HELLO não produz resposta.

## Tarefas

### 1. Admissão e prontidão

- [x] Escrever testes para duas posições, terceira rejeitada, candidato anônimo descartado, apelidos iguais, MATCH e READY/GO ordenados.
- [x] Rodar `PYTHONPATH=src python3 -m unittest tests.test_server` e observar falha antes de criar o controlador.
- [x] Implementar pacote, ações e transições mínimas; aprovar os testes.

### 2. Jogo e encerramento

- [x] Acrescentar testes para BOARD/ATTACK encaminhados apenas ao outro, KEEPALIVE, direção/fase e sintaxe inválidas.
- [x] Acrescentar testes para KO, falhas antes/durante o jogo, parada, resultado imutável e entradas tardias.
- [x] Observar testes falharem antes de implementar esses comportamentos.
- [x] Implementar ações e decisão única; aprovar testes e suíte completa.

### 3. Integração documentada e revisão

- [x] Atualizar README, IMPLEMENTATION e contexto para indicar controlador pronto e transporte/CLI/timers pendentes.
- [x] Criar relatório em docs/superpowers/reports com API, evidência, limitações e próxima etapa.
- [x] Conferir ausência de comentários e imports do cliente/socket; revisar resultados e diff sem staged/commit.

## Foco de revisão

Identificação parcial e falha de um candidato; apelidos duplicados e identidade por conexão; READY repetido e autorização antes de efeitos; duas derrotas/falhas próximas e envio indisponível; callbacks e mensagens tardias após resultado. Cada condição deve ter teste observável nas tarefas acima.

## Progresso

Tarefas 1–3 concluídas. Baseline: 97 testes; admissão/prontidão: oito; controlador completo: 28; suíte: 125 aprovados. Revisão executada sem agentes. Relatório em `../reports/2026-10-07-controlador-partida.md`.
