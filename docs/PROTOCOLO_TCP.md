# Contrato TCP TVP/1

Este contrato detalha `00-contexto-geral.md`, seções 5–8, para os dois executáveis. As cópias deste documento nos repositórios de interface e servidor devem permanecer idênticas. Cada conexão representa um participante; o servidor aceita duas posições por partida, sem identificador no fio. A física e a pontuação pertencem ao cliente. O servidor valida mensagens, fase e resultado, e encaminha o tabuleiro fixo e os ataques ao único adversário.

## Formato e limites

Cada frame é uma linha ASCII `TVP/1|TIPO[|campo...]\n`. LF é o único delimitador. Não há escape, CR, espaços extras ou campo vazio. O limite é 512 bytes incluindo LF. O receptor acumula bytes até LF, pode receber vários frames em um `recv` e rejeita a conexão se o fragmento atingir 512 bytes antes de LF. A interpretação ocorre somente após um frame completo. ASCII proíbe caracteres multibyte; uma sequência UTF-8, inclusive fragmentada, é inválida quando a linha estiver completa. Prefixo, tipo, quantidade e valor dos campos são validados pelo codec; direção, fase e combinações de resultado são validadas nos adaptadores.

| Mensagem | Emissor → destinatário | Campo e limite | Fase e efeito | Inválidos e duplicados |
| --- | --- | --- | --- | --- |
| `HELLO` | Cliente → servidor | `apelido`: 1–20 `[A-Za-z0-9_]` | Primeiro frame em até 5 s da admissão; identifica a conexão. O segundo HELLO válido produz dois MATCH. | Ausente, duplicado ou malformado: PROTOCOL; antes de identificação, apenas descarta a conexão e libera a posição. Apelidos iguais são válidos. |
| `MATCH` | Servidor → cada cliente | `apelido_oponente`: mesma regra | Após dois HELLO; cliente passa à preparação. | Cliente não o envia; duplicata ou fora de fase recebida pelo cliente interrompe a sessão sem resultado confirmado. |
| `READY` | Cliente → servidor `PLAYER`/`REMATCH`; servidor → cliente `GO` | Um token `PLAYER`, `REMATCH` ou `GO` | PLAYER após MATCH marca prontidão. Após ambos PLAYER, um GO por cliente autoriza o jogo. Após KO, dois REMATCH dentro de 10 s autorizam outra rodada da mesma dupla com GO; votos duplicados não contam novamente. | PLAYER repetido na preparação ou atrasado após GO não tem efeito. GO de cliente ou PLAYER do servidor é PROTOCOL. |
| `BOARD` | Cliente → servidor → adversário | 200 dígitos `[0-8]`, linhas de 10 por 20; só blocos fixos | Jogo ativo; substitui retrato visual pendente, sem revelar peça ativa ou pontuação. Cliente envia ao iniciar e após fixação. | Antes de GO, formato inválido ou direção errada é PROTOCOL. Após decisão, ignorar. |
| `ATTACK` | Cliente → servidor → adversário | `1`, `2` ou `4`, quantidade de lixo | Jogo ativo; encaminhar intacto na ordem. | Mesma política de BOARD; nunca descartar ou substituir ataque. |
| `KO` | Cliente → servidor | `SPAWN`, `OVERFLOW` ou `INACTIVITY` | Jogo ativo; primeira decisão válida produz LOSE/KO ao remetente e WIN/KO ao adversário. | Antes de GO é PROTOCOL; após decisão, ignorar. |
| `GAMEOVER` | Servidor → cliente | Resultado `WIN`, `LOSE` ou `CANCEL`; motivo `KO`, `DISCONNECT`, `TIMEOUT`, `PROTOCOL` ou `SERVER_STOP` | Encerramento, inclusive antes de GO com CANCEL. A decisão é gravada antes do envio. | Cliente não o envia. Resultado incompatível com motivo/fase interrompe a sessão; duplicata após resultado é ignorada. |
| `KEEPALIVE` | Ambas as direções | Sem campos | A cada 5 s depois de HELLO; válido durante espera, preparação, jogo e espera do resultado. Renova atividade, sem resposta imediata. | Antes de HELLO ou com campo é PROTOCOL. Não cria ciclo de eco. |

Exemplos de bytes: `TVP/1|HELLO|Ana\n`, `TVP/1|READY|PLAYER\n`, `TVP/1|ATTACK|2\n`, `TVP/1|GAMEOVER|WIN|KO\n`, `TVP/1|KEEPALIVE\n`. BOARD contém `TVP/1|BOARD|` seguido dos 200 dígitos e LF.

## Estado e falhas

O servidor mantém duas conexões admitidas, inclusive as que aguardam HELLO. A terceira é fechada sem mensagem adicional. Desconexão, sintaxe inválida ou prazo de HELLO vencido antes da identificação libera a posição e não cancela o jogador identificado. Depois de HELLO, a primeira falha ou KO processado decide a partida. Processar entradas sequencialmente evita dois resultados para KOs simultâneos. Nenhum efeito de jogo é encaminhado após a decisão.

Cada lado guarda o instante monotônico da última mensagem **completa e válida** recebida. O cliente inicia o prazo de inatividade ao conectar; o servidor após o HELLO. Inatividade por 15 s produz TIMEOUT no servidor; no cliente, encerra como resultado não confirmado. Bytes parciais não renovam o prazo. O envio de KEEPALIVE inicia após HELLO e ocorre a cada 5 s mesmo com tráfego de jogo.

Antes de GO, falha de participante identificado produz `CANCEL|DISCONNECT`, `CANCEL|TIMEOUT` ou `CANCEL|PROTOCOL` ao outro. Durante o jogo, produz `WIN|motivo` ao outro; o LOSE do participante ausente fica apenas no estado interno. Parada planejada envia `CANCEL|SERVER_STOP` a ambos. Depois de KO, envia `WIN|KO` e `LOSE|KO`. O resultado fica imutável diante de desconexão ou falha de envio posterior. Após KO com os dois clientes conectados, o servidor mantém a dupla por 10 s para decidir a revanche. Dois READY|REMATCH no prazo iniciam uma rodada nova com READY|GO, preservando conexões e apelidos. Sem acordo, fecha os sockets e limpa a partida. Nas demais finalizações, ou se alguém sai, tenta drenar GAMEOVER por até 1 s antes de limpar.

Cada conexão limita a saída não enviada a 4096 bytes; excesso é falha de conexão. A interface limita as filas de intenções e eventos a 256 cada. Escritas podem ser parciais: manter o restante até enviá-lo, sem misturar frames. Se o outro lado fecha, recusa a conexão ou para de progredir, liberar recursos e comunicar falha; o cliente nunca inventa vitória após perder conexão.

O servidor conserva no máximo 1024 registros locais recentes por rodada. Esse limite não descarta mensagens ou altera o resultado. Cada passagem do dispatcher atende até 32 tentativas de admissão antes de voltar aos jogadores e temporizadores; uma solicitação de parada impede novas admissões. Esses limites são locais e não acrescentam campos ou tipos ao protocolo.

Ao sair pelo teclado o cliente fecha o socket. O modo local e a simulação não usam TVP/1. O cliente aceita IP literal IPv4/IPv6 ou `localhost` como destino; `localhost` usa `127.0.0.1`. Essa restrição evita resolução DNS bloqueante no fluxo que precisa encerrar prontamente e respeitar o prazo de conexão de 5 s. Após drenar e limpar uma partida, o mesmo processo servidor volta a aceitar duas novas conexões; há no máximo uma partida ativa por vez e novas duplas usam conexões novas. A revanche conserva as conexões da dupla anterior. Esta decisão atualiza a antiga regra de reiniciar o servidor após cada partida.

## Spins e combos sem alteração no fio

O motor divide dano total em quantidades de 4, 2 e 1, preservando a soma.
Todos os ATTACK de uma fixação precedem BOARD e eventual KO. O servidor
encaminha as quantidades intactas na ordem e conserva resultado único.
Não há mensagem de spin ou combo; essas informações e score são locais.
Veja [REGRAS_JOGO.md](REGRAS_JOGO.md). Voltar ao menu fecha a conexão;
uma nova dupla usa sessões novas; a revanche conserva a identificação anterior.

## Inatividade de teclado

O cliente mede o tempo monotônico desde a última tecla durante PLAYING.
Mais de 20 s sem tecla interrompem a física e enviam KO|INACTIVITY uma única
vez; o resultado continua WIN/KO e LOSE/KO, decidido pelo servidor. Qualquer
tecla renova o prazo, inclusive uma tecla sem ação; redimensionamento do
terminal não conta. Espera e preparação não contam. O prazo de rede de 15 s
continua independente: KEEPALIVE não renova atividade de teclado.
