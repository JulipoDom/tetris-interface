# Estado atual — 08/10/2026

Cliente e servidor têm transporte TVP/1, validação de fases, encaminhamento
BOARD/ATTACK, resultado único, limpeza e partidas sequenciais. O cliente
separa worker de rede e thread de curses; o servidor usa selectors.

Disponíveis: atalhos ./client e ./server; menu configurável; reserva e três
giros; spins, combos/B2B e kicks agressivos; derrota após mais de 20 s sem
tecla; --no-timeout; revanche por dois votos em 10 s; impressão de IP/porta
na abertura da escuta com hostname -I e fallback para ip.

## Entrega e validação

Os remotos são JulipoDom/tetris-interface e JulipoDom/tetris-server, branch
main. A atualização preserva o histórico existente e remove todos os
arquivos de testes automatizados por solicitação explícita do proprietário.
Os relatórios Markdown permanecem; não há suíte distribuída em tests/.

Antes da remoção: cliente 200 testes, OK com 3 skips; servidor 93 testes, OK
com 6 skips. Os skips são verificações que dependem de sockets bloqueados
pelo ambiente. Veja [RELATORIO_VALIDACAO.md](RELATORIO_VALIDACAO.md).
Não foi demonstrada aqui uma partida TCP real entre duas máquinas.

## Verificação manual pendente

1. Em ambiente com sockets liberados, iniciar ./server e conferir IP/porta.
2. Abrir dois ./client usando o endereço, confirmar prontidão com Enter.
3. Jogar, enviar lixo e conferir o tabuleiro adversário e resultado.
4. Pressionar R nos dois clientes e confirmar rodada reiniciada sem estado velho.
5. Sem revanche, aguardar 10 s e conectar outra dupla.
6. Deixar um cliente sem teclas por mais de 20 s; repetir com --no-timeout.
7. Sair/desconectar um cliente e encerrar servidor com Ctrl+C para conferir avisos.

O comando hostname deste ambiente não oferece -I; ip também não consegue
consultar interfaces no sandbox. A detecção fora dele depende dos utilitários
da máquina. As tabelas de rotação são próprias, inspiradas no TETR.IO.
