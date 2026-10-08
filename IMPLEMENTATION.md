# Implementação atual — tetris-interface

Atualizado em 08/10/2026. O projeto deixou a fase de boilerplate e implementa
os recursos descritos no [README](README.md). O contrato detalhado está em
[PROTOCOLO_TCP.md](docs/PROTOCOLO_TCP.md) e as regras em
[REGRAS_JOGO.md](docs/REGRAS_JOGO.md).

O cliente possui motor puro, interface curses, menu, treino, worker TCP, spins, combos, reserva, kicks agressivos, inatividade opcional e revanche.

Os atalhos executáveis selecionam o fluxo usual: ./client abre o menu e
./server inicia a escuta em todas as interfaces na porta 8765 e mostra os IPs.
Comentários explicativos em português acompanham as funções do código próprio.

Os testes automatizados foram removidos a pedido do proprietário; os relatos
anteriores continuam em Markdown. A evidência e as limitações estão em
[RELATORIO_VALIDACAO.md](docs/RELATORIO_VALIDACAO.md), com o roteiro manual em
[STATUS_TCP.md](docs/STATUS_TCP.md). A comparação Python recente está em
[ESTILO_AUTOR.md](docs/ESTILO_AUTOR.md), separada das evidências históricas.
