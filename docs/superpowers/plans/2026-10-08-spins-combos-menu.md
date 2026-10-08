> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Plano de implementação: menu, resultado, spins e combos

**Objetivo:** executar o desenho aprovado e permitir edição de IP e porta no menu.
**Arquitetura:** menu externo cria partidas independentes; motor avalia jogadas;
servidor conserva o domínio sequencial e o protocolo TVP/1.
**Tecnologias:** Python, curses e unittest, sem dependências novas.
**Desenho:** `../specs/2026-10-08-spins-combos-menu-design.md`.
**Execução:** nesta sessão, conforme pedido explícito para iniciar. Sem commits
ou publicação; preservar arquivos já modificados. Comentários em português.

## Tarefas e interfaces

1. Navegação e resultado (`ui.py`, `app.py`, `network.py`).
   `_menu` retorna `(modo, apelido, host, porta)` ou None. Tab muda o campo;
   setas escolhem Prática/Multiplayer/Sair; Enter valida apelido e destino
   multiplayer. `q` fecha a App em `finally` e volta ao menu, inclusive na CLI.
   `_finish_match(result)` centraliza o encerramento; `winner` deriva o nome
   confirmado. Testar configurações inválidas, IPv6, saída, duas partidas,
   cancelamento, apelidos iguais e resultado persistente em PTY.
2. Jogadas (`engine.py`, novo `scoring.py`, novo `rotation.py`).
   `detect_spin(piece, board, rotated)` retorna None, `T-spin`, `T-spin mini`
   ou `<peça>-spin`. `evaluate_clear(kind, spin, lines, combo, back_to_back)`
   retorna registro imutável com score/ataque/contadores. Usar tabelas propostas,
   multiplicação racional para combo e bônus de singles via bit_length.
   Kicks próprios por ângulo; a peça mantém orientação. Testar cantos, bloqueios,
   movimentos reais/rejeitados, mini, demais peças, kicks e estado após hold.
3. Ataques e servidor (`engine.py`, `match.py`, `app.py`, ambos protocolos).
   Produzir eventos de 4, 2 e 1 antes de BOARD/KO; servidor os encaminha
   intactos. Refatorar validação de participante/oponente e mensagens locais
   em português, mantendo resultado imutável e oito tipos. Testar o fluxo
   dividido e resultado único, incluindo passagem pelo codec dos dois projetos.
4. Documentação e verificação.
   Atualizar regras, controles, guia de aplicação do estilo e status nos dois
   projetos; documentos compartilhados idênticos. Executar ambas as suítes,
   PTY, simulações e conferir whitespace/diffs. Reportar sockets ignorados.

## Ciclo por tarefa

- [x] Criar regressões e observar falha antes da implementação.
- [x] Implementar menu/resultado e verificar testes afetados.
- [x] Criar regressões de spin/combo/kicks e observar falhas.
- [x] Implementar avaliação, integrar fixação e verificar testes afetados.
- [x] Validar ataques divididos, refatorar servidor e verificar invariantes.
- [x] Revisar documentos e executar as duas suítes completas.

## Pontos de revisão

- Não deixar thread/sessão antiga influenciar outra partida.
- Não inventar vencedor após queda de conexão ou cancelamento.
- Não confundir rotação rejeitada com última ação efetiva.
- Não truncar ataque nem publicar KO antes de seus ataques e snapshot.
- Não chamar kicks e balanceamento próprios de implementação exata do TETR.IO.

## Registro

Desenho aprovado em 08/10/2026; pedido adicional: editar IP e porta no menu.
Decisão: Tab alterna campos sem interferir em q dentro do apelido.

Decisão registrada: a orientação é derivada das células da peça para evitar
um estado duplicado. Porta inválida no treino usa a última porta válida;
multiplayer exige validar IP e porta antes de iniciar a sessão.
Revisão independente concluiu sem achados pendentes após as correções.
