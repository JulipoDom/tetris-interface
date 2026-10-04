# Código que a equipe precisa implementar

O motor, menu, controles, nomes e fluxo da aplicação já têm implementação
local. O trabalho pendente é a comunicação real e o servidor. Todos os métodos
abaixo continuam levantando `NotImplementedError` com `TODO[EP-REDE]`.

Revisão de estado: **04/10/2026**. A suíte local tem **56 testes aprovados**.
O menu oferece Prática e Multiplayer; a simulação permanece na CLI. O atraso
de fixação vai de 800 a 200 ms, reduzindo 50 ms a cada 30 segundos ativos,
sem reiniciar o prazo por movimento ou giro. A espera mantém o atraso inicial
e a pausa do treino preserva o prazo restante.

A reserva usa `C` uma vez por fixação; `Z` gira anti-horário, `X`/↑ horário
e `A` gira 180°. O 7-bag continua embaralhando as sete peças de cada grupo.
Essas ações são locais e não acrescentam tipos ao protocolo: a reserva não
trafega em BOARD. Uma troca com spawn bloqueado publica BOARD → KO/SPAWN;
uma troca válida não publica eventos nem aplica lixo pendente.

## 1. Protocolo — `src/tetris_shared/protocol.py`

| Método | O que implementar |
| --- | --- |
| `encode(message_type, fields)` | Validar campos e produzir ASCII com prefixo `TVP/1`, separadores `\|` e LF final. |
| `parse(line)` | Validar prefixo, tokens e campos; devolver `MessageType` e campos. Validar direção e estado também no adaptador/controlador. |
| `Framer.feed(data)` | Acumular bytes por conexão, extrair todas as linhas completas, preservar o fragmento restante e recusar linha maior que 512 bytes, incluindo LF. |

Usar os oito tipos de `models.MessageType`, sem mensagens adicionais. BOARD
contém 200 dígitos de blocos fixos, linha por linha, sem a peça ativa. Um
`recv()` pode entregar parte de uma mensagem ou várias mensagens juntas.
A gramática completa está na seção 7 de [00-contexto-geral.md](00-contexto-geral.md).

## 2. Adaptador cliente — `src/tetris_client/network.py`

| Método | Responsabilidade |
| --- | --- |
| `NetworkSession.start(nickname)` | Conectar ao servidor TCP e enviar **HELLO com esse apelido**. Preparar buffers, relógios monotônicos e estado da conexão. |
| `ready()` | Enviar READY com PLAYER; não iniciar a física local. |
| `offer_board(board)` | Enviar BOARD dos blocos fixos, com cópia independente. |
| `attack(amount)` | Enviar ATTACK com 1, 2 ou 4 linhas de lixo. |
| `defeat(reason)` | Enviar KO com SPAWN ou OVERFLOW; continuar conectado esperando GAMEOVER. |
| `poll()` | Processar I/O sem bloquear, preservar escritas parciais, alimentar framing/parser e devolver eventos tipados. |
| `close()` | Fechar a conexão e liberar buffers; suportar fechamento repetido. Não enviar uma mensagem extra de saída. |

`poll()` também agenda KEEPALIVE a cada 5 segundos após HELLO e detecta 15
segundos sem mensagem completa e válida. KEEPALIVE não deve ser ecoado.
Respeitar o limite de saída de 4096 bytes; não descartar ataques silenciosamente.
O futuro adaptador também precisa definir como receber endereço/porta do
servidor: ainda não há configuração de endereço na CLI nem no menu.

## 3. Integração dos nomes e eventos

O caminho do nome local está pronto:

```text
ui._menu → App.nickname → App.start → NetworkSession.start(nickname) → HELLO
```

Na simulação, o último passo é `FakeSession.start`, que registra
`HelloOffered(nickname)` em memória. Não são bytes nem envio real.

O caminho do nome remoto também está pronto:

```text
MATCH recebido → OpponentDefined(apelido_remoto) → App.update → App.opponent → ui._render
```

O adaptador deve transformar mensagens recebidas nestes eventos existentes:

| Mensagem recebida | Evento interno |
| --- | --- |
| MATCH | `OpponentDefined(nickname)` |
| READY com GO | `StartAuthorized()` |
| BOARD | `BoardReceived(snapshot)` |
| ATTACK | `AttackReceived(amount)` |
| GAMEOVER | `MatchResult(result, reason)` |
| Falha/fechamento sem resultado | `ConnectionLost()` |

Não ecoar BOARD ou ATTACK recebidos. A aplicação já espera autorização antes
de jogar e conserva a ordem ataque → snapshot → derrota ao publicar uma
fixação. Não mudar essa ordem no buffer de saída.

`ui._run` já usa `NetworkSession` para a opção Multiplayer. Enquanto `start`
for um stub, exibe indisponibilidade e volta ao menu, preservando o nome.
Não trocar esse adaptador pelo fake para apresentar multiplayer funcionando.

## 4. Servidor — frente ainda não criada

Criar `tetris_server` conforme o contexto geral e o boilerplate do servidor
quando fornecido. Admitir duas conexões, validar HELLO em até 5 segundos,
enviar MATCH com o nome do outro jogador, esperar ambos os READY/PLAYER e
autorizar com READY/GO. Encaminhar boards e ataques, registrar uma decisão
única e finalizar após tentar escoar as notificações por até 1 segundo.

Rejeitar terceira conexão. Tratar KO, desconexão, timeout, violação de
protocolo e parada do servidor conforme a seção 8 do contexto. O servidor
não simula a física. Uma nova partida exige reiniciar servidor e clientes.

## 5. Validação da comunicação real

Adicionar testes de mensagens fragmentadas e agrupadas, campos inválidos,
limites de buffers, escritas parciais, HELLO/KEEPALIVE/timeouts e desconexões.
Depois testar dois clientes contra o servidor: nomes distintos, prontidão,
ataques, boards e um único resultado confirmado. Os testes locais atuais
não comprovam funcionamento da rede.

## 6. Verificação local e pendências de interface

```bash
.venv/bin/python -m unittest discover -s tests
# Sem ambiente instalado:
PYTHONPATH=src python3 -m unittest discover -s tests
```

`tests/test_client.py` reúne 26 testes de motor, aplicação, fake, modelos e
stubs. `tests/test_menu_and_delay.py` reúne 14 testes de menu, apelidos,
cabeçalhos, fixação e pausa. `tests/test_hold_and_rotation.py` reúne 16 testes
de reserva, giros, controles na TUI e garantias do 7-bag.
A renderização usa uma tela substituta, sem
terminal real. A validação visual/interativa em Linux/WSL continua necessária.

No fake demonstrativo, o primeiro BOARD oferece o snapshot remoto fixo.
O quinto BOARD local agenda uma linha de lixo: corresponde à quarta fixação,
pois o BOARD de início também é contado. Depois o ataque se repete a cada
cinco fixações. Esse roteiro não implementa física de um segundo jogador.

## Onde ajustar o jogo já implementado

- `src/tetris_shared/rules.py`: gravidade e constantes do atraso de fixação.
- `src/tetris_client/engine.py`: `lock_delay`, `_touch_ground`, `tick`,
  `pause` e `resume` controlam o prazo sem reset infinito por movimento;
  `hold` e `rotate(turns)` implementam reserva e giros.
- `src/tetris_client/ui.py`: `_menu` controla opções/nome e `_render` mostra
  os cabeçalhos dos jogadores.
- `tests/test_menu_and_delay.py`: testes determinísticos das mudanças.
- `tests/test_hold_and_rotation.py`: reserva, giros, teclas e 7-bag.

## A implementação manual fica só em tetris_shared?

Não. `src/tetris_shared/protocol.py` contém `encode`, `parse` e `Framer.feed`
para implementar o codec e o framing TVP/1. A sintaxe e a semântica estão nas
seções 6–8 de `00-contexto-geral.md`.

Também é preciso implementar `src/tetris_client/network.py` para conexão
TCP, I/O, buffers, eventos e timers, definir endereço/porta na interface ou
CLI e criar o servidor `tetris_server`. O motor e a TUI já usam a porta de
sessão; não precisam incorporar sockets ou serialização. Os stubs de rede
e protocolo continuam com `TODO[EP-REDE]` nesta entrega.
