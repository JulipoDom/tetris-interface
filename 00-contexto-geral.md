# Contexto atual do Tetris Versus

Atualizado em 08/10/2026. Python 3.12+, biblioteca padrão em execução,
cliente curses em Linux/WSL e servidor TCP direto. Os projetos têm ambientes
Python separados porque distribuem pacotes com nomes compartilhados.

## Partida e responsabilidades

Cada rodada tem dois jogadores; o servidor mantém somente uma rodada ativa e
aceita novas duplas após a limpeza. O cliente calcula física, score, spins,
combos e lixo; o servidor valida fases e payloads, encaminha ataques/tabuleiros
e determina um resultado único. Não há salas, contas, ranking, persistência,
reconexão ou partidas simultâneas.

Fases: WAITING, PREPARING, PLAYING e FINISHED. Dois HELLO definem a dupla;
cada jogador confirma READY|PLAYER e somente READY|GO autoriza o jogo.
Apelidos: 1–20 caracteres ASCII, letras, números ou underscore.

## Regras e encerramento

Tabuleiro 10×20, sete peças, reserva uma vez por peça, previsão da próxima,
gravidade de 0,7 s e fixação entre 0,8 s e 0,2 s conforme o tempo ativo.
Rotação horária, anti-horária e 180° com kicks agressivos; destino deve caber
sem sobreposição. Spins, combos e B2B seguem [REGRAS_JOGO.md](docs/REGRAS_JOGO.md).
A implementação é inspirada no TETR.IO, com regras próprias.

Ataques são divididos em mensagens de 4, 2 e 1 linha. Fixação publica ataques,
depois BOARD, depois eventual KO. Lixo aplica até quatro linhas por fixação;
o limite pendente é 40. O servidor não transmite score nem a peça ativa.

Mais de 20 s sem tecla durante PLAYING causa KO|INACTIVITY; redimensionar o
terminal não conta. --no-timeout desativa somente essa derrota no cliente.
Após KO confirmado, R solicita revanche por 10 s. Dois votos reiniciam a
rodada na mesma conexão. Sem acordo, o cliente volta ao menu e o servidor
limpa a dupla. Saída, falha de protocolo e rede seguem o contrato abaixo.

## Protocolo e concorrência

[PROTOCOLO_TCP.md](docs/PROTOCOLO_TCP.md) define exatamente oito tipos TVP/1:
HELLO, MATCH, READY, BOARD, ATTACK, KO, GAMEOVER e KEEPALIVE. Frames ASCII
terminados por LF, até 512 bytes. BOARD contém 200 dígitos de 0 a 8.
HELLO vence em 5 s; KEEPALIVE a cada 5 s e silêncio de rede vence em 15 s.
Esses prazos são independentes da atividade de teclado.

Cliente: thread principal controla curses/motor; worker controla socket,
bytes e temporizadores, comunicando por filas. Servidor: selectors e despacho
sequencial modificam o estado. O primeiro encerramento válido fixa o resultado.
As duas cópias de tetris_shared/protocol.py devem permanecer idênticas.

## Documentação e validação

README.md explica execução; docs/STATUS_TCP.md registra estado e limitações;
docs/ESTILO_AUTOR.md reúne evidências de estilo. Planos e relatórios antigos
são registros históricos, não instruções de execução atuais.

Por solicitação do proprietário, todos os arquivos de testes automatizados
foram removidos em 08/10/2026; os relatórios Markdown foram conservados.
A validação anterior à remoção está em docs/RELATORIO_VALIDACAO.md. Não execute
unittest discover -s tests: a pasta já não faz parte da distribuição.
