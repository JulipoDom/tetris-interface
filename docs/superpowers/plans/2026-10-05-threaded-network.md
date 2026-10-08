> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Plano de correção: estrutura de threads sem comunicação implementada

**Objetivo:** devolver TCP e protocolo aos stubs e conservar somente a estrutura
concorrente que a equipe usará para implementar a comunicação.
**Especificação:** [estrutura concorrente](../specs/2026-10-05-threaded-network-design.md)
**Execução:** neste workspace, com outro agente dedicado à tradução dos comentários.

- [x] Substituir testes de TCP/codec por testes da estrutura concorrente e dos stubs.
- [x] Confirmar falhas antes de retirar a implementação anterior.
- [x] Remover sockets, bytes, codec, delimitação e temporizadores funcionais.
- [x] Conservar início de thread, filas de objetos, ordem FIFO, consulta e parada.
- [x] Deixar pontos explícitos TODO[EP-REDE] nos métodos de comunicação.
- [x] Restaurar aviso no menu e erro da CLI para a rede pendente.
- [x] Traduzir comentários/docstrings com outro agente, preservando a AST funcional.
- [x] Corrigir README, contexto, boilerplate e guia de implementação.
- [x] Rodar a suíte completa e conferir ausência de implementação TCP no código.

## Registro

A estrutura usa tipos Python existentes de intenções/eventos, sem
novos tipos de mensagens. Limites de bytes, framing, timers e regras do protocolo
permanecem requisitos futuros. O servidor não foi criado nesta etapa.
A publicação no GitHub foi solicitada explicitamente após a conclusão do esquema.

Verificação em 05/10/2026: `.venv/bin/python -m unittest discover -s tests`,
74 testes aprovados, sem testes ignorados.
