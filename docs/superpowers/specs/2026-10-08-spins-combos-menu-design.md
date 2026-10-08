> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Refatoração, resultado, menu, spins e combos

Estado: aprovado pelo usuário em 08/10/2026 e implementado nesta sessão.
Pedido adicional aprovado: editar IP e porta no menu inicial.
Detalhes executáveis: `../../REGRAS_JOGO.md`.

## Objetivo e pedidos

Refatorar cliente e servidor seguindo as evidências de `docs/ESTILO_AUTOR.md`,
com comentários em português que expliquem decisões e funções. Corrigir os
problemas encontrados, identificar o vencedor na tela após o nocaute e
implementar spins e combos inspirados no TETR.IO. Sair de uma partida retorna
ao menu; a opção de sair do menu encerra o programa.

Preservar Python, biblioteca padrão, curses, duas pessoas, uma partida ativa,
oito tipos TVP/1 e as alterações locais preexistentes nos dois repositórios.

## Diagnóstico verificado

- `ui._run` encerra a função inteira ao receber `q`; o menu não é retomado.
- `App.update` exibe o resultado individual, mas não identifica o vencedor.
- O motor gira sem deslocamentos corretivos e não registra spins ou combos.
- ATTACK aceita somente 1, 2 ou 4, tanto no codec quanto nos consumidores.
- Os testes atuais passam: cliente 149, com 2 ignorados; servidor 77, com 6
  ignorados. O ambiente impede testes de integração com sockets reais.
- Já existe um guia de estilo com evidências históricas. Reutilizar suas
  inferências e limites, sem atribuir ao autor convenções Python não comprovadas.

## Alternativas

1. **Recomendação:** detecção de T-spin e spins das demais peças, combos e
   bônus simples de sequência; dividir ataques maiores em frames existentes.
   Mantém a comunicação compatível e exige regras próprias explicitadas abaixo.
2. Implementar apenas T-spin e combos. Menor alcance, mas não oferece spins
   das outras peças.
3. Replicar integralmente um modo específico do TETR.IO. Exige escolher modo,
   versão, rotação e tabelas exatas antes de projetar o balanceamento completo.

A página oficial do [TETR.IO](https://tetr.io/) oferece diferentes opções de
spins, combos e kicks. A recomendação é uma adaptação para este projeto;
não promete reproduzir integralmente a física ou o balanceamento desse jogo.

## Menu e encerramento

Manter um loop externo de menu e um loop interno de partida. `q` durante
espera, preparação, jogo ou resultado sai do loop interno. Seu `finally`
fecha a aplicação e a sessão antes de abrir o menu. Isso vale também para
entrada direta pela CLI. Mostrar `q: menu` no jogo e uma opção explícita de
saída no menu, mantendo Esc para encerrar no menu.

Nova partida cria App, Engine e Session novos; conserva apelido e endereço
configurados. Não reutilizar conexão nem transportar score, lixo, reserva,
combo, eventos ou resultado da partida anterior. Sair durante multiplayer
continua sendo desconexão para o servidor.

## Resultado visível

O resultado depende de GAMEOVER confirmado. WIN identifica o jogador local
como vencedor e LOSE identifica o oponente já recebido por MATCH. Apelidos
iguais devem ser acompanhados de `você` ou `oponente` para distinguir os lados.
CANCEL informa ausência de vencedor. Perda de conexão sem GAMEOVER conserva
`resultado não confirmado`. O treino termina sem inventar adversário.

Exibir nome do vencedor e motivo em uma tela final persistente. Não sair
automaticamente no nocaute; `q` permite voltar ao menu. Extrair a finalização
de `App.update` para uma função direta e testável.

## Spins, combos e ataques propostos

Derivar orientação das células e registrar a última ação que efetivamente mudou a peça; movimento
rejeitado não altera o registro. Spawn e hold reiniciam esse estado. Descida
que muda a posição invalida a rotação anterior; queda instantânea de distância
zero preserva a rotação. Detectar o spin antes de gravar a peça ou limpar linhas.

T-spin exige última ação de rotação e três dos quatro cantos em volta do
pivô ocupados; bordas contam como ocupadas. Os dois cantos na direção da
frente da peça distinguem spin completo de mini. Outras peças, exceto O,
usam detecção de imobilidade após rotação: não conseguem mover para esquerda,
direita ou baixo. Acrescentar deslocamentos corretivos de rotação com tabela
documentada e testes específicos; não chamar uma tabela própria de SRS+.

Combo conta fixações consecutivas com limpeza: primeira limpeza é combo 0,
segunda é 1. Uma fixação sem limpeza reinicia o contador. Hold não constitui
fixação. Mostrar tipo do último spin, quantidade de linhas e combo no painel.

Manter base de ataques normais 0/0/1/2/4 para zero a quatro linhas. T-spin
completo envia 0/2/4/6 para zero a três linhas; mini envia 0/0/1 para zero
a duas. Spins das outras peças recebem identificação e mantêm sequência
difícil, usando ataque normal como base. Uma sequência difícil é formada por
quad ou spin com limpeza; a partir da segunda, acrescenta uma linha. Limpeza
comum quebra essa sequência; peça sem limpeza a preserva.

Para combos, aplicar multiplicador `1 + combo / 4` ao ataque base com bônus
de sequência, arredondando para baixo. Singles sem ataque base ganham bônus
`floor(log2(1 + combo))`. Essa fórmula é uma escolha de adaptação a revisar,
não uma alegação de equivalência ao TETR.IO. Pontuação permanece local; manter
tabela normal e documentar tabela de spins e bônus `50 * combo` por limpeza.

Dividir o ataque total em mensagens de 4, depois 2, depois 1, preservando a
soma. Todos os ataques da fixação precedem BOARD e eventual KO. O servidor
continua validando e encaminhando cada quantidade, sem importar a física.
Manter o limite de 40 linhas pendentes e a aplicação de até 4 por fixação.
Cancelamento de lixo e sistemas adicionais de balanceamento ficam fora desta
proposta.

## Refatoração e validação

No cliente, separar resultado, avaliação da jogada, publicação e navegação
em funções pequenas com nomes descritivos. No servidor, revisar validação,
finalização e mensagens de erro em português, preservando resultado imutável
e despacho sequencial. Manter as cópias do protocolo idênticas e atualizar
documentação de regras, controles e limites nos dois projetos.

Antes de cada correção, criar regressão que falhe no código anterior.
Testar vencedor em WIN/LOSE/CANCEL, apelidos iguais, resultado tardio,
retorno ao menu em todos os estados, criação de uma segunda partida sem
resíduos, restauração do terminal e encerramento da sessão.

Testar detecção positiva e negativa de spins, movimentos bloqueados,
rotação/hold/spawn, kicks, quebra de combo, sequência difícil, pontuação,
soma e ordem dos ataques divididos e seu encaminhamento pelo servidor.
Executar as duas suítes e testes de curses em PTY. Registrar os testes com
sockets ignorados como limitação, sem afirmar integração TCP real validada.
