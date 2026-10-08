# Regras atuais: spins, combos, resultado e menu

Atualização aprovada em 08/10/2026. As cópias nos dois projetos devem permanecer
idênticas. Este documento substitui as restrições históricas do MVP que
excluíam kicks, spins e combos. Física e score continuam exclusivos do cliente.

## Menu e resultado

Setas escolhem Prática, Multiplayer ou Sair. Tab alterna Apelido, IP e Porta;
Shift+Tab volta ao campo anterior. Digite para acrescentar caracteres e use
Backspace para apagar. Enter confirma a seleção; Esc encerra no menu.
Multiplayer aceita IPv4, IPv6 ou localhost e porta de 1 a 65535. Configuração
inválida mostra o erro e mantém o menu aberto, sem iniciar sessão.

`q`/`Q` durante a partida fecha a sessão e retorna ao menu, inclusive quando
iniciada diretamente por `--mode`. O menu conserva apelido, IP e porta válidos.
Prática funciona sem destino de rede válido; porta apagada ou inválida conserva
a última porta válida. Cada nova partida cria motor e sessão novos, sem lixo,
score, reserva, combo, tabuleiro ou resultado da rodada anterior.

Após GAMEOVER, o jogo congela e a tela mostra vencedor e motivo por até 10 s.
`R` pede revanche; no multiplayer, ambos devem votar nesse prazo, e no treino
o reinício é imediato. Sem acordo, a interface volta ao menu. `q` permite sair.
WIN identifica o jogador local; LOSE identifica o nome recebido por MATCH.
Os qualificadores `você` e `oponente` distinguem apelidos iguais. Cancelamento
não tem vencedor. Perda de conexão sem GAMEOVER não confirma nenhum resultado.
O treino termina sem declarar vencedor de uma partida multiplayer.

## Detecção de spins

Antes de gravar a peça no tabuleiro, verificar a última ação efetiva.
Uma rotação válida registra a possibilidade de spin. Translação efetiva,
incluindo queda suave, gravidade e queda instantânea com deslocamento,
invalida essa possibilidade. Movimento ou rotação rejeitados não a alteram.
Queda instantânea de distância zero pode confirmar o encaixe. Spawn e hold
reiniciam o registro; hold não reinicia combo nem sequência difícil.

T-spin exige rotação como última ação efetiva e três dos quatro cantos do
quadrado 3×3 ocupados. Bordas também contam como ocupadas. A orientação é
derivada das células, sem um contador duplicado. Os dois cantos na frente
da ponta do T distinguem spin completo de mini: ambos ocupados = completo.
Mini que fecha três linhas usa a tabela completa.

I, S, Z, J e L recebem identificação de spin quando, após rotação, não
podem transladar para esquerda, direita ou baixo. O não produz spins.
Os spins dessas peças usam a tabela normal de score e ataque e contam
como limpeza difícil quando removem linhas.

## Rotação e kicks

O giro transforma as células dentro do quadrado original: `(x, y)` vira
`(tamanho - 1 - y, x)` por quarto de volta. A posição final de 180° é
avaliada diretamente. y negativo significa subir; positivo significa descer.

Primeiro, tentar os kicks anteriores na mesma ordem, preservando os encaixes
já possíveis:

| Giro | Deslocamentos (dx, dy) |
| --- | --- |
| Horário | (0,0), (-1,0), (1,0), (0,-1), (-2,0), (2,0), (0,-2) |
| 180° | (0,0), (0,-1), (-1,0), (1,0), (0,-2), (-2,0), (2,0) |
| Anti-horário | (0,0), (1,0), (-1,0), (0,-1), (2,0), (-2,0), (0,-2) |

Se todos falharem, tentar os encaixes agressivos, nesta ordem:
`(0,1), (-1,1), (1,1), (-1,-1), (1,-1), (0,2), (-1,2), (1,2),
(-1,-2), (1,-2), (-2,-1), (2,-1), (-2,1), (2,1), (-2,-2), (2,-2),
(-2,2), (2,2)`. Esses deslocamentos permitem descer e girar sob saliências
ou alcançar cavidades na diagonal. Valida-se o destino, sem exigir que a
peça transladada ou uma orientação intermediária de 180° caiba no caminho.

A peça I ainda tenta `(-3,0), (3,0), (-3,-1), (3,-1), (-3,1), (3,1)`
quando todas as correções anteriores falham. No anti-horário, os deslocamentos
extras são espelhados horizontalmente para preferir o lado oposto.
O alcance é limitado a duas colunas e duas linhas, com até três colunas para I;
O continua sem kicks ou identificação de spin.

Nenhum kick pode sobrepor blocos ou sair dos limites com uma célula ocupada.
Girar não reinicia o prazo de fixação. Kicks válidos contam como rotação para
reconhecer spins; a tabela de score e ataques continua a mesma.
Estas regras são uma adaptação própria inspirada nos encaixes de
[TETR.IO](https://tetr.io/); as tabelas deste projeto não reproduzem SRS+.

## Score e ataque base

| Jogada | 0 linhas | 1 linha | 2 linhas | 3 linhas | 4 linhas |
| --- | --- | --- | --- | --- | --- |
| Normal: score / ataque | 0 / 0 | 100 / 0 | 300 / 1 | 500 / 2 | 800 / 4 |
| T-spin: score / ataque | 400 / 0 | 800 / 2 | 1200 / 4 | 1600 / 6 | — |
| T-spin mini: score / ataque | 100 / 0 | 200 / 0 | 400 / 1 | usa T-spin | — |

Combo começa em -1; primeira fixação com limpeza o leva a 0, segunda a 1,
e assim por diante. Fixação sem linha reinicia combo em -1. Cada limpeza
acrescenta `50 × combo` ao score; sem linha, não há bônus de combo.

Sequência difícil (B2B) começa em 0. Quad ou spin com limpeza incrementa a
sequência; limpeza comum a reinicia em 0. Fixação sem limpeza a preserva.
Da segunda limpeza difícil em diante, acrescentar uma linha ao ataque base.

Ataque final = `floor((base + bônus B2B) × (1 + combo / 4))`.
Para single cujo ataque base com B2B permanece zero, usar
`floor(log2(1 + combo))`. Uma fixação sem linhas nunca ataca.
O painel mostra jogada, linhas, combo, B2B e ataque local calculado.

Exemplo: três quads consecutivos enviam 4, 6 e 7 linhas. O segundo envia
`ATTACK|4` e `ATTACK|2`; o terceiro envia 4, 2 e 1. Toda soma é preservada.

## Contrato e lixo

TVP/1 mantém oito tipos e quantidades ATTACK de 1, 2 ou 4. O motor divide
totais maiores em 4, depois 2, depois 1. Publicar todos esses ataques antes
de BOARD e eventual KO. O servidor valida e encaminha cada mensagem intacta,
sem simular nem validar a execução física de um spin.

Lixo recebido espera a fixação; aplicar até quatro linhas por peça e
preservar o restante. Mais de 40 linhas pendentes causa falha de sessão,
não KO artificial. Não há cancelamento de lixo nesta adaptação.

Referência de inspiração: a interface oficial do [TETR.IO](https://tetr.io/)
oferece opções diferentes de spins, tabela de combo e kicks. A detecção e
o balanceamento descritos aqui são escolhas deste projeto, sem equivalência
integral prometida a um modo competitivo do TETR.IO.

## Inatividade e opção de execução

Mais de 20 s sem tecla durante PLAYING causa derrota INACTIVITY. Qualquer
tecla renova o prazo; resize não conta. Espera e preparação não contam.
./client --no-timeout desativa somente essa regra, inclusive em novas rodadas;
KEEPALIVE e timeout de rede continuam independentes.
