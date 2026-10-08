> Registro histórico: descreve o planejamento ou a validação na data do arquivo.
> O estado atual está em [STATUS_TCP.md](../../STATUS_TCP.md). Os arquivos de
> testes automatizados foram removidos em 08/10/2026; comandos/contagens abaixo
> permanecem como evidência histórica, sem representar uma suíte distribuída.

# Protocolo compartilhado TVP/1 — plano de implementação

**Objetivo:** implementar codec e delimitação conforme `00-contexto-geral.md`, seção 7, e `IMPLEMENTATION.md`.
**Arquitetura:** módulo puro compartilhado; nenhuma conexão, timer ou mudança no motor. APIs públicas `encode`, `parse`, `Framer.feed` preservadas; novos identificadores em português e código sem comentários.
**Execução:** sequencial neste checkout, autorizada pelo usuário; sem commits ou novos agentes.

## Contrato e decisões

- `encode(tipo_mensagem, campos)` recebe MessageType e tupla de strings, devolve bytes ASCII com LF.
- `parse(linha)` recebe exatamente uma linha de bytes incluindo LF, devolve MessageType e tupla de strings.
- Argumentos Python de tipo incorreto geram TypeError; conteúdo ou linha inválida gera ValueError.
- Apelidos ASCII de 1–20 caracteres, BOARD de 200 dígitos 0–8, demais tokens conforme gramática. Nenhuma normalização de espaços, CR ou encoding.
- Direção, fase e combinações semânticas de GAMEOVER pertencem ao adaptador. O codec aceita as combinações da gramática, sem inferir estado da partida.
- Framer por conexão, retorna linhas incluindo LF, aceita múltiplas linhas e conserva fragmento. Limite de 512 bytes por linha incluindo LF: fragmento sem LF pode ter no máximo 511 bytes.
- Delimitação não interpreta sintaxe. Após excesso, libera fragmento e permanece inválida: conexão deve ser encerrada, não ressincronizada silenciosamente.
- Limite de saída de 4096 bytes, sockets e temporizadores permanecem pendentes em network.py.

## Etapas

- [x] Substituir testes de stubs por exemplos literais dos oito tipos, entradas inválidas e testes de fragmentação/limites; observar falha antes da implementação.
- [x] Implementar validação compartilhada, encode/parse e Framer; passar testes do protocolo.
- [x] Atualizar o teste de fronteira para exigir somente os stubs de transporte e rodar toda a suíte.
- [x] Atualizar guia, contexto e README para distinguir protocolo pronto de transporte pendente. Registrar aceite da interface informado pelo usuário.
- [x] Conferir diff, ausência de comentários novos e resultados finais.

## Revisão

Cobrir delimitadores injetados em campos, Unicode confundível com ASCII, campos extras/ausentes, tamanho em bytes incluindo LF e excesso dividido entre chamadas. Exercitar todos os pontos de divisão de um fluxo e instâncias independentes. Nenhum teste deve abrir socket.

## Evidência de execução

18 testes do protocolo falharam inicialmente por NotImplementedError. Após a implementação, os 18 passaram; a suíte completa passou com 97 testes. Ver relatório em `../reports/2026-10-07-protocolo-compartilhado.md`.
