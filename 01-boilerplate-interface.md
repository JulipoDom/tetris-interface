# Boilerplate da interface - dois jogadores

**Atualização em 07/10/2026:** o usuário confirmou a interface pronta e
funcionando. O protocolo compartilhado foi implementado por solicitação
explícita; os requisitos abaixo de codec/framing vazios pertencem à geração
inicial do boilerplate. TCP, estados da sessão e timers continuam pendentes.
Veja [IMPLEMENTATION.md](IMPLEMENTATION.md) para o contrato atual.

**Atualização em 05/10/2026:** foi acrescentado somente o esquema de threads,
filas e parada do cliente. Os requisitos de stubs continuam válidos para TCP,
codec, framing e temporizadores. Consulte [IMPLEMENTATION.md](IMPLEMENTATION.md)
para os pontos a preencher; o servidor também continua pendente.

## 1. Instrução para gerar o código

Ler junto de `00-contexto-geral.md`, a fonte única das regras e do protocolo inicial. Criar um cliente Python com TUI `curses`, motor local completo e sessão simulada em memória. Existem apenas o jogador local e um oponente.

Implementar o produto local. **Não implementar a comunicação nesta etapa:** sockets, parsing, serialização, framing, buffers e timers de rede ficam com `TODO[EP-REDE]` e `NotImplementedError`. A especificação inicial já nomeia os oito tipos, mas sua execução em rede será trabalho da equipe.

Os comandos e caminhos abaixo descrevem o código a gerar; os Markdown não são o código do boilerplate.

**Estado em 05/10/2026:** o código do cliente descrito aqui já existe neste
checkout. Menu, nomes, fixação progressiva, pausa e estrutura concorrente estão
implementados. A suíte tem 74 testes aprovados, incluindo reserva, giros,
stubs e estrutura de threads; comunicação real e servidor continuam pendentes.
Consultar [README.md](README.md) para executar e
[IMPLEMENTATION.md](IMPLEMENTATION.md) para integrar o adaptador real.

## 2. Estrutura pequena

| Arquivo | Responsabilidade |
| --- | --- |
| `src/tetris_client/__main__.py` | Escolher modo local, simulated ou network. |
| `src/tetris_client/engine.py` | Tabuleiro, peças, ações, tempo, lixo, score e derrota local. |
| `src/tetris_client/ui.py` | Entrada de teclado e renderização do terminal. |
| `src/tetris_client/app.py` | Coordenar telas, motor e porta de sessão. |
| `src/tetris_client/session.py` | Porta tipada e FakeSession sem rede. |
| `src/tetris_client/network.py` | Esquema de thread, filas e parada; comunicação em stubs. |
| `src/tetris_shared/models.py` | Tipos internos, cópias do tabuleiro e enum dos oito tipos. |
| `src/tetris_shared/rules.py` | Constantes e tabela de score/ataque do contexto geral. |
| `src/tetris_shared/protocol.py` | Encoder, parser e framing TVP/1 implementados. |
| `tests/test_client.py` | Testes do motor e da aplicação com fake. |
| `tests/test_menu_and_delay.py` | Testes do menu, nomes, atraso de fixação e pausa. |
| `tests/test_hold_and_rotation.py` | Reserva, giros, controles e garantias do 7-bag. |
| `tests/test_network.py` | Threads, ordem das filas, limites, falhas e parada, sem sockets. |
| `tests/test_protocol.py` | Validação de campos, codec e framing incremental. |
| `tests/test_network_entrypoints.py` | Endereço/porta e aviso de rede pendente na CLI/menu. |

Não criar catálogo de salas, seleção de partida, fila de matchmaking ou IDs de partida. Criar o pacote compartilhado uma vez no repositório, não duplicá-lo em cada frente.

## 3. Motor local

Implementar as regras da seção 4 do contexto geral: matriz 10×20, peça ativa separada, 7-bag, gravidade de 700 ms, atraso de fixação de 800 ms reduzido até 200 ms com o tempo ativo, reserva, giros horários, anti-horários e de 180° sem wall kicks, score e ataque por limpeza, lixo aplicado entre peças e top out objetivo. A queda instantânea ainda fixa imediatamente.

### Formas iniciais

Usar matrizes quadradas de tamanho fixo, sem recortar os espaços vazios após girar. Coordenadas locais `(x,y)`:

| Peça | Tamanho | Células ocupadas |
| --- | --- | --- |
| I | 4 | (0,1), (1,1), (2,1), (3,1) |
| O | 2 | (0,0), (1,0), (0,1), (1,1) |
| T | 3 | (1,0), (0,1), (1,1), (2,1) |
| S | 3 | (1,0), (2,0), (0,1), (1,1) |
| Z | 3 | (0,0), (1,0), (1,1), (2,1) |
| J | 3 | (0,0), (0,1), (1,1), (2,1) |
| L | 3 | (2,0), (0,1), (1,1), (2,1) |

Giro horário: `(x,y)` vira `(n-1-y,x)`; anti-horário vira `(y,n-1-x)`;
180° vira `(n-1-x,n-1-y)`. O não muda. Recusar integralmente movimento ou
rotação se qualquer célula ocupada no destino for inválida. Para 180°, não
validar o giro intermediário. Spawn em `y=0`, `x=(10-n)//2`. Células vazias
da matriz da peça não causam colisão.

Hold guarda o tipo da peça, sem conservar posição ou rotação. A primeira
reserva consome a próxima da fila; trocas posteriores preservam a fila.
Só permitir uma troca até a fixação, respeitando pausa e estados da aplicação.
Spawn bloqueado na troca produz snapshot → derrota, sem alterar blocos,
pontuação ou lixo pendente. Mostrar a reserva ao lado da próxima peça.

Usar passo de tempo com relógio monotônico injetável; não vincular a gravidade à quantidade de redesenhos. No loop, limitar trabalho de recuperação de atrasos a um máximo documentado, sem congelar teclado e desenho. RNG de lixo separado do RNG de peças.

O motor devolve ocorrências locais de ataque produzido, snapshot consolidado e derrota. Não envia mensagens. Copiar o snapshot: desenhar ou encaminhar uma projeção não pode mudar o tabuleiro. Em uma fixação que ataca e perde, preservar a ordem definida no contexto geral.

## 4. Telas e interação

| Estado da aplicação | Tela e comportamento |
| --- | --- |
| Menu | Escolher Prática ou Multiplayer e editar o apelido. Multiplayer informa indisponibilidade e retorna ao menu enquanto a rede estiver pendente; simulação permanece acessível pela CLI. |
| Espera | Após iniciar sessão, mostrar “Aguardando outro jogador”. Isso não é uma confirmação de admissão pelo servidor. |
| Preparação | Após MATCH, mostrar o oponente e “Enter para ficar pronto”. |
| Pronto | Após confirmar, aguardar autorização de início; não mover peças ainda. |
| Jogando | Tabuleiro local, próxima peça, score, lixo pendente e último tabuleiro remoto. |
| Aguardando resultado | Após derrota local, parar física; continuar consultando a sessão. |
| Encerrado | Exibir resultado confirmado ou cancelamento, sem tentar outra partida na mesma conexão. |
| Interrompido | Sem decisão recebida: “Resultado não confirmado”. |

O treino começa diretamente e termina em “Fim do treino”. Simulação exibe permanentemente “SIMULAÇÃO LOCAL - SEM REDE”. Não mostrar ping fictício. A falta de snapshot remoto mostra “Aguardando tabuleiro do oponente”.

Na execução padrão, abrir o menu antes do treino. Acima do tabuleiro local, mostrar o nome escolhido; acima do remoto, mostrar o nome do evento de oponente definido (futuro MATCH), com “Aguardando jogador” enquanto não houver nome. O apelido é entregue à porta de sessão para o futuro HELLO. A pausa do treino congela também o atraso de fixação e a progressão desse atraso.

Controles: setas para mover/descer; ↑/X para giro horário; Z anti-horário;
A para 180°; C para guardar/trocar; espaço para queda instantânea; Enter
para prontidão; `q` para sair. Aceitar minúsculas e maiúsculas para Z/X/A/C.
Na simulação, `b`/`B` cancela, `v` injeta vitória e `d` desconexão.
Saída fecha a sessão e é abandono se a partida estiver ativa. Não oferecer
pausa unilateral durante jogo em sessão. Treino pode pausar.

Alvo visual: terminal de pelo menos 80×28, tabuleiros lado a lado, cores com fallback monocromático, células com dois caracteres de largura. Em terminal pequeno, exibir aviso sem paralisar o loop. Todas as chamadas de `curses` ficam no mesmo fluxo. Restaurar o terminal em exceção ou saída; logs em arquivo.

## 5. Porta de sessão, sem rede

Expor métodos internos para iniciar com apelido, confirmar prontidão, oferecer tabuleiro, informar ataque, informar derrota, fechar e consultar eventos disponíveis. Trabalhar com objetos tipados; não usar strings serializadas no fake.

A aplicação consome eventos internos de oponente definido, início autorizado, tabuleiro recebido, ataque recebido, resultado e conexão perdida. KEEPALIVE e tempos de rede são responsabilidade do futuro adaptador, não do motor ou da TUI.

| Ocorrência local | Tradução futura pela equipe |
| --- | --- |
| Abrir sessão com apelido | HELLO |
| Oponente informado | MATCH recebido |
| Confirmar prontidão | READY com PLAYER |
| Receber autorização de início | READY com GO |
| Snapshot após início/fixação | BOARD |
| Ataque de 1, 2 ou 4 linhas | ATTACK; não informar quantidade de linhas limpas como payload. |
| Derrota local única | KO |
| Resultado/cancelamento | GAMEOVER recebido |
| Manter/verificar atividade | KEEPALIVE no adaptador; não visível como ação de jogo. |

Só iniciar a física após o evento de autorização. Ataque recebido aumenta o contador pendente; nunca é ecoado. Snapshot remoto substitui a cópia anterior; não é retransmitido. GAMEOVER encerra imediatamente o motor, mesmo sem derrota local. Após KO, ainda é preciso receber GAMEOVER e manter a sessão viva.

No treino, ataques gerados não precisam de oponente. No fake, registrar saídas e injetar entradas determinísticas: espera, MATCH conceitual, autorização, ataque, snapshot e resultado. Simular também conexão perdida e cancelamento. Não abrir socket, gravar canal em arquivo nem esconder comunicação dentro do mock.

## 6. Estrutura de threads e stubs a preservar

- `network.py` já fornece `_start_worker`, `_enqueue`, `_publish`, `poll`, `close`
  e o laço `_run`. O jogo e todas as chamadas curses permanecem na thread principal.
- `start`, `ready`, `offer_board`, `attack` e `defeat` continuam stubs. A equipe
  deve validar os estados e ligar essas entradas aos auxiliares das filas.
- `_connect`, `_send`, `_receive_events`, `_process_timers` e `_close_connection`
  continuam stubs de comunicação, chamados pela futura thread de rede.
- `tetris_shared/protocol.py`: representar, delimitar e validar os oito tipos descritos no contexto.
- Métodos pendentes levantam `NotImplementedError` com `TODO[EP-REDE]`.
- O `close` já implementado somente controla a thread. Liberar socket e buffers
  pertence ao ponto pendente `_close_connection`, executado no `finally` do laço.
- `--host` e `--port` configuram o destino futuro; ainda não estabelecem conexão.
- O comando de rede encerra com código não zero e explica que falta implementar o adaptador. Nunca iniciar fake automaticamente.

Modos esperados depois da geração:

```bash
python -m tetris_client --mode local
python -m tetris_client --mode simulated
python -m tetris_client --mode network
python -m unittest discover -s tests
```

## 7. Aceite do boilerplate

Estado conferido por testes automatizados em 05/10/2026. O usuário confirmou
o aceite geral em 07/10/2026: “interface esta pronta e funcionando”.

Atualização de 07/10/2026: os 74 testes existentes e oito novos testes de
integração curses em PTY passaram (82 no total), antes do protocolo; veja o [registro e roteiro](docs/superpowers/reports/2026-10-07-milestone-01.md).

- [x] Treino jogável: aceite geral da interface confirmado pelo usuário.
- [x] Tabela comum de score e ATTACK respeitada; zero ataque não gera evento.
- [x] Lixo espera o fim da peça, aplica até quatro linhas e preserva o restante.
- [x] Spawn bloqueado e transbordamento produzem derrota única.
- [x] Score e lixo são zerados em nova execução local.
- [x] Fake demonstra prontidão e início distintos, além de resultado e interrupção.
- [x] Tabuleiro remoto é cópia dos blocos fixos, sem animar física remota.
- [x] Motor pode ser testado sem terminal, relógio real ou socket.
- [x] Stubs de transporte continuam vazios; modo de rede não afirma estar funcionando.
- [x] Menu oferece Prática e Multiplayer e permite editar o apelido.
- [x] Nome local chega à sessão; nome remoto atualiza o cabeçalho após o evento.
- [x] Prazo de fixação não reinicia com movimento e nunca fixa uma peça no ar.
- [x] Espera mantém 800 ms; pausa preserva prazo e progressão do atraso.
- [x] Reserva em C permite uma troca por fixação e mostra a peça guardada.
- [x] Z/X/A giram nos dois sentidos e 180°, respeitando colisão e prazo.
- [x] Cada bag contém todas as sete peças; sorteios não têm três iguais seguidas.
- [x] Estrutura concorrente preserva ordem das intenções e mantém o jogo separado.
- [x] Consulta de eventos e parada não esperam por uma operação de rede bloqueada.
- [x] TCP e temporizadores continuam pendentes; codec e framing implementados.
- [x] Comentários e docstrings do código próprio estão em português.

Verificação: `.venv/bin/python -m unittest discover -s tests` — 74 testes,
`OK`. Sem instalação: `PYTHONPATH=src python3 -m unittest discover -s tests`.

O README deve explicar instalação, controles e o fato de que uma nova partida real exige reiniciar o servidor. Não adicionar funções fora desse escopo.
