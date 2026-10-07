# Tetris Versus — interface

Base funcional do cliente Python para Tetris 1vs1 no terminal: motor local,
TUI `curses`, treino e sessão simulada em memória. A implementação segue
[o contexto geral](00-contexto-geral.md) e
[o boilerplate da interface](01-boilerplate-interface.md).

**Comunicação TCP pendente para implementação pela equipe.** O cliente contém
o esquema de uma thread de rede com filas e sinal de parada. Conexão, envio,
recepção e temporizadores são stubs `TODO[EP-REDE]` que levantam
`NotImplementedError`. O pacote `tetris_server` contém o controlador puro
da partida; seu executável e transporte TCP ainda não foram implementados.

## Atualização — 07/10/2026

- Interface aceita pelo usuário após a validação do milestone 1.
- Protocolo compartilhado implementado: oito tipos, ASCII estrito, campos
  validados, LF obrigatório e delimitação incremental com limite de 512 bytes.
- Controlador do servidor implementado: admissão, prontidão, encaminhamento,
  falhas e resultado único. 125 testes aprovados (28 do controlador).
- TCP, estados do adaptador cliente, temporizadores e executável servidor pendentes.
- Contrato das APIs em [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Estado histórico — 05/10/2026

- Menu padrão com Prática e Multiplayer, edição do apelido e cabeçalhos com
  nomes local/remoto implementados; simulação acessível por `--mode simulated`.
- Atraso de fixação progressivo implementado, com prazo único por peça e
  pausa que preserva o tempo restante. Durante a espera, a tela mostra 800 ms.
- Reserva de peça em `C`, giro anti-horário em `Z`, horário em `X`/↑ e
  180° em `A`. Gerador 7-bag preservado, sem sequência fixa.
- Testes de motor, interface, stubs e estrutura concorrente, sem sockets.
- Estrutura de thread de rede, filas de intenções/eventos e fechamento implementada.
  TCP, codec TVP/1, validação de estados e temporizadores ficam para a equipe.
- `--host` e `--port` guardam o destino da futura conexão; não abrem rede nesta etapa.
- Comentários e docstrings do código próprio em português; 74 testes aprovados.

O auxiliar `_start_worker` está preparado, mas `start` continua stub. A thread
de rede só será habilitada no modo network quando você implementar os pontos
de comunicação descritos em [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Instalação

Use Python 3.12 ou superior, com a mesma versão menor na equipe, em Linux ou
Linux/WSL com `curses`. Terminal recomendado: pelo menos 80 colunas × 28 linhas.
Não há dependências externas de execução; o empacotamento usa setuptools.

```bash
python3 -c "import curses"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Execute na raiz do projeto:

```bash
python -m tetris_client                         # menu e edição do apelido
python -m tetris_client --mode local            # treino imediato
python -m tetris_client --mode simulated --nickname Jogador_A
python -m tetris_client --mode network --host 127.0.0.1 --port 8765 # rede pendente
python -m unittest discover -s tests
```

O comando instalado `tetris_client` aceita os mesmos argumentos. Apelidos
aceitam de 1 a 20 caracteres ASCII: letras, números e `_`.

Para trabalhar sem instalação do pacote, defina `PYTHONPATH` na raiz e use os
mesmos comandos com `python3`:

```bash
export PYTHONPATH="$PWD/src"
python3 -m tetris_client --mode local
python3 -m unittest discover -s tests
```

## Controles e telas

| Tecla | Ação |
| --- | --- |
| ← / → | Mover |
| ↓ | Descer uma linha; ao apoiar, aguardar o prazo de fixação |
| ↑ / `X` | Girar no sentido horário, sem wall kicks |
| `Z` | Girar no sentido anti-horário, sem wall kicks |
| `A` | Girar 180°, validando a posição final |
| `C` | Guardar/trocar peça; uma vez até a próxima fixação |
| Espaço | Queda instantânea e fixação |
| Enter | Confirmar prontidão após o oponente ser informado |
| `p` | Pausar/retomar somente o treino |
| `q` | Sair e fechar a sessão |

`C`, `Z`, `X` e `A` também aceitam letras minúsculas.
No menu, cima/baixo selecionam o modo; digite o apelido, use Backspace para
editar, Enter para iniciar e Esc para sair.

A execução padrão (`python -m tetris_client`) abre o menu com **Prática** e
**Multiplayer**. Enquanto a rede estiver pendente, Multiplayer informa
indisponibilidade e retorna ao menu, preservando o apelido. O modo explícito
`--mode network` informa o TODO e encerra com código 2 em terminal interativo.
`--host` e `--port` configuram o destino futuro (padrão: `127.0.0.1:8765`).
O nome escolhido aparece acima do seu tabuleiro e será enviado em HELLO após
a implementação. A simulação continua explícita pela CLI, sem comunicação real.
O modo network nunca usa a sessão simulada automaticamente.

O treino começa diretamente e encerra com “Fim do treino”. A simulação mostra
permanentemente “SIMULAÇÃO LOCAL - SEM REDE”: espera → oponente informado →
Enter para prontidão → autorização → jogo → resultado. Seu roteiro fornece
um snapshot fixo do oponente e uma linha de lixo após a quarta fixação local,
depois a cada cinco fixações. O snapshot inicial também conta no roteiro.
O oponente demonstrativo não tem física nem inteligência artificial.

Na simulação, `v` injeta vitória durante o jogo, `b` injeta cancelamento e `d`
injeta desconexão. A derrota local agenda um resultado de derrota no fake;
até recebê-lo, a aplicação continua consultando a sessão com a física parada.
Desconexão mostra resultado não confirmado. Nenhuma dessas ações abre rede.

A TUI usa dois caracteres por célula, cores com fallback monocromático e
tabuleiros lado a lado. O tabuleiro remoto contém apenas blocos fixos. Em
terminal pequeno aparece um aviso, mas eventos, teclado e física continuam
processando. `curses.wrapper` restaura o terminal em saída ou exceção; logs
ficam em `logs/tetris-client.log`.

## Regras implementadas

Tabuleiro 10×20 sem linhas ocultas, sete peças em 7-bag, próxima peça e
gravidade fixa de 700 ms. Cada giro preserva a matriz quadrada original.
Ao apoiar, a peça permanece móvel por **800 ms** para permitir ajustes e giros.
Esse atraso diminui **50 ms a cada 30 segundos de jogo ativo**, até **200 ms**.
O prazo é definido no primeiro contato de cada peça e não reinicia com
movimentos, giros ou tentativas de descer. A peça nunca fixa enquanto estiver
no ar; se voltar ao apoio depois do prazo, fixa na próxima atualização.
Espaço ainda fixa imediatamente. A pausa do treino congela o prazo e a
progressão; espera por outro jogador também não conta. A TUI mostra o atraso
atual em milissegundos.

Cada grupo de sete peças sorteadas contém I, O, T, S, Z, J e L uma vez,
embaralhadas novamente a cada bag. Duas peças iguais podem se encontrar na
fronteira entre bags; três iguais consecutivas na sequência sorteada são
impossíveis. A reserva pode alterar a ordem em que as peças são jogadas.

A reserva aparece na lateral. Quando vazia, `C` guarda a peça ativa e traz
a próxima; quando ocupada, troca as peças sem consumir a próxima da fila.
A peça que entra nasce na posição e orientação iniciais, com novos relógios
de gravidade e apoio. Só é possível guardar/trocar uma vez até a fixação.
A ação não fixa blocos, pontua, aplica lixo ou envia BOARD quando bem-sucedida.
Se o nascimento estiver bloqueado, produz snapshot e derrota por SPAWN.
Espera, pausa e fim do jogo impedem a troca.

Giros horários, anti-horários e de 180° preservam a matriz quadrada e são
permitidos durante o atraso de fixação, sem reiniciar seu prazo. O giro de
180° valida apenas o destino, sem exigir espaço para o giro intermediário.
Não há wall kicks, níveis, combos, pontuação de T-spins ou pontos por queda.

| Linhas limpas | Pontos | Lixo enviado |
| --- | ---: | ---: |
| 0 | 0 | 0 |
| 1 | 100 | 0 |
| 2 | 300 | 1 |
| 3 | 500 | 2 |
| 4 | 800 | 4 |

Lixo recebido espera a fixação da peça. Aplicam-se até quatro linhas por
fixação; o restante permanece pendente. Cada linha tem nove blocos e um
buraco escolhido pelo RNG de lixo, independente do gerador de peças. Mais de
40 linhas pendentes interrompem a sessão, sem produzir KO falso.

Uma fixação limpa linhas, calcula score/ataque, aplica lixo e verifica
transbordamento ou spawn bloqueado. Publica ataque, snapshot copiado e derrota,
nessa ordem. Blocos na primeira linha, sozinhos, não causam derrota.

A gravidade usa relógio monotônico injetável e recupera no máximo quatro passos
por atualização. Atraso excedente é descartado para manter teclado e desenho
responsivos; o motor não depende da quantidade de redesenhos.

## Árvore de trabalho

```text
tetris-interface/
├── 00-contexto-geral.md
├── 01-boilerplate-interface.md
├── AGENTS.md                     # Superpowers por padrão e contrato do projeto
├── README.md
├── IMPLEMENTATION.md             # pontos de integração para a equipe
├── .gitignore
├── pyproject.toml
├── .superpowers/
│   ├── LICENSE
│   ├── README.md
│   ├── provenance.json
│   └── skills/                   # 15 skills oficiais, revisão fixada
├── src/
│   ├── tetris_client/
│   │   ├── __init__.py
│   │   ├── __main__.py           # CLI e seleção de modo
│   │   ├── engine.py             # domínio puro e ocorrências locais
│   │   ├── app.py                # estados, motor e porta de sessão
│   │   ├── ui.py                 # teclado e desenho curses
│   │   ├── session.py            # porta tipada e FakeSession
│   │   └── network.py            # estrutura de thread; TCP pendente
│   ├── tetris_server/
│   │   ├── __init__.py
│   │   └── partida.py            # controlador puro da partida única
│   └── tetris_shared/
│       ├── __init__.py
│       ├── models.py             # snapshots, eventos e oito tipos
│       ├── rules.py              # constantes e tabelas comuns
│       └── protocol.py           # codec TVP/1 e delimitação incremental
└── tests/
    ├── __init__.py
    ├── test_client.py            # motor, aplicação, fake e fronteiras
    ├── test_menu_and_delay.py    # menu, nomes, prazo de fixação e pausa
    ├── test_hold_and_rotation.py # reserva, giros, teclas e garantias do 7-bag
    ├── test_protocol.py          # validação, codec e framing
    ├── test_server.py            # admissão, estados, encaminhamento e resultado
    ├── test_network.py           # estrutura de thread, filas e parada
    ├── test_network_entrypoints.py # CLI e menu multiplayer
    └── test_terminal.py          # integração curses em pseudoterminal Linux/WSL
```

Os testes usam relógios injetáveis e uma tela substituta. A estrutura concorrente
é testada com uma subclasse que substitui somente os pontos pendentes, sem
sockets ou serialização. Esses testes não comprovam comunicação TCP. Cobrem
colisão, giro, bags, gravidade, limpeza, score, lixo, top out, isolamento dos
snapshots, ordem de publicação, prontidão, resultado, cancelamento e falhas.
Também verificam seleção de modo, edição do apelido, entrega do nome à sessão,
cabeçalhos dos jogadores, atraso inicial durante a espera, redução do atraso,
pausa e prazo expirado enquanto a peça está no ar. A tela é substituída por
um objeto de teste nos testes unitários. Os oito testes de `test_terminal.py`
executam o cliente real em pseudoterminal (PTY), verificando menu, pausa,
redimensionamento, resultados simulados, rede pendente e restauração dos
atributos do terminal. Isso não substitui o aceite visual humano.

Verificação do milestone 1 em 07/10/2026, com Python 3.14.7 em Linux:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
# 82 testes — OK, sem testes ignorados.
```

O [registro e roteiro do milestone 1](docs/superpowers/reports/2026-10-07-milestone-01.md)
descreve as evidências automatizadas, o roteiro e o aceite geral informado pelo usuário.

## Próxima etapa: integração da equipe

Veja [IMPLEMENTATION.md](IMPLEMENTATION.md) para o funcionamento das threads,
os pontos de integração e a API do controlador de servidor.

`NetworkSession` fornece thread, filas, consulta de eventos e sinal de parada.
Seus pontos de conexão TCP, envio/recepção, tradução e timers continuam TODO.
`protocol.py` implementa encoder, parser e framing. Os oito tipos são
`HELLO`, `MATCH`, `READY`, `BOARD`, `ATTACK`, `KO`, `GAMEOVER` e `KEEPALIVE`.

O controlador em `tetris_server.partida` recebe mensagens tipadas e devolve
ações para o futuro transporte. O executável `tetris_server` e seus sockets
ainda precisam ser implementados. O desenho prevê dois jogadores, um servidor e uma única
partida por execução. **Uma nova partida real exige reiniciar o servidor e
os clientes.** Não reutilizar conexão encerrada nem criar gerenciador de salas.

O [relatório do controlador](docs/superpowers/reports/2026-10-07-controlador-partida.md)
registra a implementação, os testes e as responsabilidades do transporte futuro.

## Workflow dos agentes

Superpowers é o padrão deste projeto via [AGENTS.md](AGENTS.md), usando a cópia
local em `.superpowers/skills/`. Não precisa ser solicitado a cada tarefa.
Veja [origem, revisão e descoberta nativa](.superpowers/README.md).

O workflow já está ativo por meio das instruções de `AGENTS.md`. Ele usa
leitura direta das skills locais, sem exigir instalação global. A descoberta
nativa opcional é descrita em `.superpowers/README.md`.
