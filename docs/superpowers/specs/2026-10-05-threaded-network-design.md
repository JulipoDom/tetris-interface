# Estrutura concorrente para implementação pela equipe

O escopo é fornecer apenas o esquema de threads, sem
implementar TCP, serialização, parsing, delimitação ou temporizadores de rede.
Nenhuma comunicação real é executada pelo código desta etapa.

A thread principal mantém curses, App e Engine. NetworkSession oferece um
auxiliar para iniciar a thread `tetris-network`, duas filas protegidas por
um bloqueio e um evento de parada. A fila de saída transporta intenções Python
imutáveis, com HELLO primeiro e ordem FIFO para ataque, tabuleiro e derrota.
A fila de entrada transporta eventos tipados; somente App.update altera o jogo.

Os métodos públicos start, ready, offer_board, attack e defeat continuam stubs
TODO[EP-REDE]. A equipe irá conectar esses métodos aos auxiliares de concorrência.
Os pontos internos _connect, _send, _receive_events, _process_timers e
_close_connection também são stubs e serão executados pela thread de rede.
O protocolo compartilhado conserva encode, parse e Framer.feed como stubs.

O esquema limita as filas a 256 itens e processa até 32 intenções por ciclo.
Excesso ou exceção produz ConnectionLost, sem resultado inventado. poll só
consulta eventos. close sinaliza parada, espera até 200 ms e não realiza I/O;
a liberação do futuro transporte ocorre no finally da thread. A espera entre
ciclos é interrompível e limitada a 20 ms.

O modo network não inicia sessão simulada. Multiplayer informa pendência e
retorna ao menu. A CLI conserva host/port como configuração futura e retorna
código 2 para o TODO em terminal interativo. Treino e simulação continuam ativos.
Como start continua stub, a thread de rede só é iniciada nos testes que
substituem os pontos pendentes; a equipe deverá habilitá-la ao implementar TCP.

Os comentários e docstrings do código próprio em src/ e tests/ são em português,
revisados por outro agente conforme solicitação. APIs e identificadores oficiais
permanecem com seus nomes. Skills vendorizadas e licenças ficam intactas.

Os testes usam uma subclasse exclusiva de teste para os pontos pendentes, sem
sockets, bytes de protocolo ou canal externo. Verificam concorrência, propriedade
das chamadas, ordem das filas, limites, falhas e parada. Não comprovam TCP.
O servidor e os testes de comunicação real ficam para implementação posterior.
