# Tetris Versus — cliente

Cliente de terminal em Python 3.12+, com curses, treino local e multiplayer
TCP para dois jogadores. Dependências de execução: somente biblioteca padrão.
Requer terminal interativo Linux/WSL com pelo menos 80 colunas e 28 linhas.

## Abrir a interface

Na raiz do repositório:

```bash
./client
```

O menu oferece Prática, Multiplayer e Sair. Setas escolhem a opção; Tab e
Shift+Tab alternam apelido, IP e porta; Enter confirma. Use o IP da máquina
que executa o servidor e a porta padrão 8765.

Para entrar diretamente ou desativar a derrota por teclado inativo:

```bash
./client --mode local
./client --mode network --host 192.168.1.10 --port 8765 --nickname Ana
./client --no-timeout
```

--no-timeout também funciona com --mode network. Desativa somente a derrota
por mais de 20 segundos sem tecla; mantém os prazos de rede e de revanche.
Os destinos aceitos são IP literal IPv4/IPv6 ou localhost, sem DNS externo.
Apelidos têm 1–20 letras ASCII, números ou underscore.

Alternativa ao atalho:

```bash
PYTHONPATH=src python3 -m tetris_client
```

Instalação opcional em ambiente próprio: python3 -m venv .venv e
.venv/bin/pip install -e .; depois .venv/bin/tetris_client. Não instale este
projeto junto ao servidor no mesmo ambiente, pois há pacotes homônimos.

## Jogar

| Tecla | Ação |
| --- | --- |
| ← / → | Mover |
| ↓ | Queda suave |
| ↑ ou X | Girar no sentido horário |
| Z | Girar no sentido anti-horário |
| A | Girar 180° |
| Espaço | Queda instantânea |
| C | Reservar peça |
| Enter | Confirmar prontidão no multiplayer |
| P | Pausar treino local |
| R | Solicitar revanche após resultado |
| Q | Fechar sessão e voltar ao menu |

O multiplayer começa somente quando os dois jogadores ficam prontos.
Mais de 20 s sem qualquer tecla durante o jogo causa derrota; resize não
renova o prazo. Após resultado, a física para e aparece o vencedor/motivo.
Há 10 s para revanche: ambos devem pressionar R no multiplayer. No treino,
R reinicia diretamente. Sem revanche, a interface retorna ao menu.

Espaço tem uma trava fixa de 600 ms após cada queda aceita. Pressionamentos
bloqueados são descartados e não prolongam o prazo. Movimento e rotação
continuam disponíveis; segurar Espaço pode fixar uma peça a cada 600 ms.

O motor usa spins, combos, B2B e kicks agressivos para encaixes diagonais e
sob saliências. A posição final sempre respeita blocos e limites; as regras
são uma adaptação própria, sem promessa de equivalência ao SRS+ do TETR.IO.
Veja [regras completas](docs/REGRAS_JOGO.md).

## Conectar ao servidor

No repositório [tetris-server](https://github.com/JulipoDom/tetris-server),
execute ./server. Ele escuta em 0.0.0.0:8765 e mostra os IPs locais. Dois
clientes usam o mesmo IP/porta, cada um com seu apelido. Pela Tailscale,
ambos precisam ter acesso à máquina na tailnet ou por compartilhamento;
informe o IPv4 Tailscale do servidor e permita TCP 8765 nas regras de acesso
e no firewall. Não use 0.0.0.0 como destino do cliente.

## Estrutura e diagnóstico

engine.py contém a física pura; rotation.py e scoring.py calculam giros e
jogadas; app.py coordena eventos; ui.py contém curses; network.py mantém o
socket em worker com filas; session.py define a porta e o modo demonstrativo.
--mode simulated permanece uma demonstração em memória, sem adversário TCP.
Falhas do cliente são registradas em logs/tetris-client.log.

[Protocolo](docs/PROTOCOLO_TCP.md), [estado atual](docs/STATUS_TCP.md),
[guia de estilo](docs/ESTILO_AUTOR.md) e [validação](docs/RELATORIO_VALIDACAO.md)
complementam este README. Todos os testes automatizados foram removidos a
pedido do proprietário; os relatórios Markdown históricos permanecem.
