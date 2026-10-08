# Relatório de validação — 08/10/2026

## Evidência anterior à remoção dos testes

Comando executado na raiz de tetris-interface:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Resultado: **200 testes, OK, 3 ignorados**. Os ignorados dependem de
sockets indisponíveis no sandbox. Não houve falha na suíte executada.
Esse resultado pertence ao código anterior à exclusão dos arquivos de teste;
nenhuma mudança de comportamento foi feita durante a limpeza/documentação.

Todos os arquivos de testes automatizados foram removidos por solicitação
explícita do proprietário. Este relatório conserva o registro; o comando
acima é histórico e já não funciona com a distribuição sem tests/.

## Limites

Mocks e simulações não demonstram uma partida TCP real. Continua pendente
jogar com dois clientes em ambiente com sockets permitidos, incluindo
revanche, inatividade e falhas. O roteiro está em STATUS_TCP.md.

## Conferência após a limpeza

- python3 -m compileall -q src: concluído sem erros.
- git diff --check: sem erros de whitespace.
- Atalho executável com --help: opções conferidas, incluindo --no-timeout no cliente.
- Modo simulated do servidor: cenários concluídos com saída 0.
- Não restam arquivos de testes automatizados distribuídos.

A publicação usa o conector GitHub porque o SSH deste ambiente não consegue
resolver github.com. Os remotos SSH locais foram preservados.
