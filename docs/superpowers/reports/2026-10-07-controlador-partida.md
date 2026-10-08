> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Controlador da partida — relatório de implementação

Data: 07/10/2026. Branch: `feat/interface-e-protocolo-compartilhado`.
Plano: [controlador-partida](../plans/2026-10-07-controlador-partida.md).
Contrato: `00-contexto-geral.md`, seções 5–8, e `IMPLEMENTATION.md`.

## O que foi implementado

O pacote `tetris_server` contém um controlador da única partida, independente
de sockets, relógios e física. A classe recebe mensagens e falhas observadas
pelo futuro adaptador e devolve ações imutáveis em ordem.

- Limite de duas conexões admitidas, contando candidatos sem HELLO.
- Terceira conexão rejeitada com fechamento, sem afetar os jogadores existentes.
- HELLO obrigatório e único; apelidos iguais permitidos, identidade pela conexão.
- Candidato sem HELLO que falha é removido e libera sua posição.
- Identificado nunca é substituído; falha termina a única partida.
- MATCH enviado aos dois somente após ambos os HELLO válidos.
- READY/GO enviado uma vez, após READY/PLAYER de ambos. PLAYER repetido na
  preparação ou atrasado durante o jogo não reinicia a partida.
- BOARD e ATTACK válidos são encaminhados somente ao outro jogador, após GO.
- Validação sintática reutiliza o codec existente; direção e fase são
  verificadas no controlador. Cliente não pode enviar MATCH, GO ou GAMEOVER.
- KEEPALIVE só é aceito após HELLO e não gera resposta.
- KO ativo produz LOSE ao remetente e WIN ao oponente.
- DISCONNECT, TIMEOUT e PROTOCOL produzem CANCEL antes do jogo; durante
  a partida, registram LOSE para o indisponível e WIN para o oponente.
- SERVER_STOP cancela em qualquer fase, inclusive sem participantes.
- Decisão registrada antes de retornar notificações; resultados imutáveis.
- Mensagens/falhas posteriores não encaminham efeitos nem alteram a decisão;
  novas conexões após o encerramento são rejeitadas.

## Arquivos desta etapa

Criados:

- `src/tetris_server/__init__.py`: pacote do servidor.
- `src/tetris_server/partida.py`: controlador, fases, ações e decisão.
- `tests/test_server.py`: 28 testes unitários do controlador.
- `docs/superpowers/plans/2026-10-07-controlador-partida.md`: plano e progresso.
- Este relatório.

Atualizados:

- `README.md`: estado atual, árvore de arquivos, contagem e próxima etapa.
- `IMPLEMENTATION.md`: API, comportamento e integração futura do transporte.
- `00-contexto-geral.md`: controlador implementado e pendências atuais.

As alterações anteriores de interface/protocolo foram preservadas. Não houve
alteração nesta etapa em Engine, curses, NetworkSession, codec ou pyproject.toml.
Todos os identificadores novos estão em português, exceto APIs da biblioteca
padrão, tipos existentes e o prefixo test_ do unittest. Nenhum comentário foi
adicionado aos arquivos Python novos.

## API e exemplo de uso

```python
from tetris_server.partida import ControladorPartida
from tetris_shared.models import MessageType

controlador = ControladorPartida()
primeira, segunda = object(), object()
controlador.admitir(primeira)
controlador.admitir(segunda)
controlador.receber(primeira, MessageType.HELLO, ("Ana",))
acoes_match = controlador.receber(segunda, MessageType.HELLO, ("Beto",))
controlador.receber(primeira, MessageType.READY, ("PLAYER",))
acoes_inicio = controlador.receber(segunda, MessageType.READY, ("PLAYER",))
acoes_resultado = controlador.receber(primeira, MessageType.KO, ("SPAWN",))
decisao = controlador.decisao
```

As listas contêm `EnviarMensagem(conexao, tipo_mensagem, campos)` ou
`FecharConexao(conexao)`. Referências de conexão são objetos hashable estáveis
usados apenas pelo adaptador, sem IDs extras no protocolo. Não reutilizar
referências de conexões encerradas. Ações de envio podem ser serializadas
com `encode(acao.tipo_mensagem, acao.campos)`.

O futuro loop do servidor deve processar as entradas sequencialmente e executar
cada lista na ordem. A classe não tem locks nem deve ser chamada simultaneamente
por threads. `fase` e `decisao` são propriedades de consulta. A decisão guarda
motivo e resultados por conexão identificada, inclusive para o perdedor que
não pode receber uma notificação.

`falhar` aceita apenas os enums DISCONNECT, TIMEOUT e PROTOCOL. Motivos errados
são erro de uso da API (ValueError); parada planejada usa `parar`. Referência
já admitida é erro de API em `admitir`. Callbacks de conexões desconhecidas são
ignorados, e conexões novas após decisão recebem fechamento.

## Evidência de testes

- Baseline: 97 testes aprovados antes das mudanças.
- Primeira etapa RED: import do pacote falhou porque tetris_server não existia;
  depois da implementação mínima, os oito testes de admissão/prontidão passaram.
- Segunda etapa RED: 28 testes executados, com falhas nas regras de jogo,
  encerramento e métodos ainda ausentes. Logs locais:
  `/tmp/tetris-servidor-admissao-red.log` e `/tmp/tetris-servidor-jogo-red.log`.
- GREEN: os 28 testes do controlador passaram.
- Suíte completa: 125 testes aprovados, incluindo protocolo, jogo, concorrência
  e integração curses em PTY; nenhum teste ignorado.

Comandos executados:

```bash
PYTHONPATH=src python3 -m unittest tests.test_server -v
PYTHONPATH=src python3 -m unittest discover -s tests
git diff --check
```

## Revisão e decisões

Sem criar transporte artificial para testar a lógica: os testes chamam a
classe real com referências em memória e verificam ações e decisão.
O catálogo interno de ações não adiciona mensagens ao TVP/1. A disponibilidade
de conexões é atualizada antes de criar GAMEOVER, evitando prometer notificação
a quem já falhou. Encerramento impede reutilizar a partida e mantém a primeira
ocorrência válida mesmo se o envio posterior falhar ou ambos desconectarem.

A revisão conferiu as políticas de identificação parcial, apelidos iguais,
GO antes de encaminhamento, mensagens na direção errada, READY idempotente,
KO antes do jogo como PROTOCOL, falhas em cada fase e callbacks tardios.
Não houve subagentes, commits, staging ou publicação.

## O que permanece pendente

O controlador aceita eventos de timeout, mas não mede tempo nem gera timers.
O futuro transporte deverá implementar socket/listen/accept, framing/parser,
HELLO em até 5 s, KEEPALIVE a cada 5 s e inatividade de 15 s. Erros de parser
ou framing deverão chamar `falhar(conexao, EndReason.PROTOCOL)`.

Também faltam buffers de saída de 4096 bytes, escritas parciais, associação
real das conexões, executável tetris_server e integração TCP no cliente.
Após fase ENCERRADA, o transporte deverá tentar enviar GAMEOVER por até 1 s,
fechar as conexões e terminar. O controlador não fecha imediatamente os
clientes alcançáveis que precisam receber GAMEOVER; rejeitados/infratores e
candidatos anônimos recebem ação de fechamento imediato.

Esses testes não demonstram comunicação TCP. A próxima etapa é construir
o adaptador de transporte do servidor e o executável, reutilizando este
controlador e o protocolo compartilhado; depois integrar o cliente real.
