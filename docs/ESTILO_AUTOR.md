# Evidências do estilo de Julio Domingos

Este guia registra padrões observados em código anterior a **8 de outubro de 2024**, dois anos antes desta missão. A amostra usa commits atribuídos à conta `JulipoDom` e às identidades informadas em `CONTEXTO_CODEX_TCP.md`. Inspecionei os diffs dos commits e o conteúdo dos arquivos **naqueles SHAs**, sem usar a versão atual dos repositórios como prova de antiguidade. Autoria do commit é uma evidência de autoria das mudanças do diff, não de cada linha preexistente nem de todo arquivo enviado em lote.

| Repositório e commit histórico | Data (UTC) | Arquivo e prova de autoria | Alcance da amostra |
| --- | --- | --- | --- |
| [JulipoDom/EcstasyRiddle, `d4019f8`](https://github.com/JulipoDom/EcstasyRiddle/commit/d4019f8c9f4a36eaced5dca1b8f6bfd10d0fd361) | 2022-10-02 | O diff atribuído a `JulipoDom` (`101841660+JulipoDom@users.noreply.github.com`) adiciona [`js/fase1.js`](https://github.com/JulipoDom/EcstasyRiddle/blob/d4019f8c9f4a36eaced5dca1b8f6bfd10d0fd361/js/fase1.js), `fase1.html` e altera `css/style.css`. | Interação simples de jogo, DOM e apresentação. O commit [6fcef56](https://github.com/JulipoDom/EcstasyRiddle/commit/6fcef56f1c59115cefb9c3501d105a8d29ced473), de 2022-11-18, também foi inspecionado para verificar textos e organização da interface. |
| [JulipoDom/CalculadoraMaria, `89945ee`](https://github.com/JulipoDom/CalculadoraMaria/commit/89945ee76927c94ec35584e9ec82ade15d9c5090) | 2024-02-10 | O diff atribuído a `Julio Domingos das Neves Neto` (conta `JulipoDom`) altera [`src/calculator.js`](https://github.com/JulipoDom/CalculadoraMaria/blob/04d4af86eb5241b3fd69f556c676e93d52e5c416/src/calculator.js): extrai `doOperation`, acrescenta o estado `firstNumber` e trata operações sucessivas. Correções posteriores no mesmo arquivo: [`a430a5f`](https://github.com/JulipoDom/CalculadoraMaria/commit/a430a5f96071af71b3b3727be14ff7fdee988994) e [`04d4af8`](https://github.com/JulipoDom/CalculadoraMaria/commit/04d4af86eb5241b3fd69f556c676e93d52e5c416). | JavaScript com estado e eventos. Repositório privado acessível pela conexão GitHub nesta análise; os links exigem acesso ao repositório. |
| [Svetly-Company/Belifter-mobile-employee, `8e5f24b`](https://github.com/Svetly-Company/Belifter-mobile-employee/commit/8e5f24b0b37cbb09d9e384d001144791598a42db) | 2024-07-16 | O commit tem autor e conta `JulipoDom`, email `jdnn2006@gmail.com`. O diff adiciona [`src/classes/WeekDays/WeekDays.tsx`](https://github.com/Svetly-Company/Belifter-mobile-employee/blob/8e5f24b0b37cbb09d9e384d001144791598a42db/src/classes/WeekDays/WeekDays.tsx), [`src/components/WeeklyDiary/index.tsx`](https://github.com/Svetly-Company/Belifter-mobile-employee/blob/8e5f24b0b37cbb09d9e384d001144791598a42db/src/components/WeeklyDiary/index.tsx) e [`src/app/loginScreen.tsx`](https://github.com/Svetly-Company/Belifter-mobile-employee/blob/8e5f24b0b37cbb09d9e384d001144791598a42db/src/app/loginScreen.tsx). | TypeScript/React Native. É um commit de importação em lote (`passing files to main`); pode conter material de outras pessoas. Por isso, padrões vistos só nele recebem confiança limitada. |

| Padrão observado | Evidência histórica | Confiança | Aplicação ao Tetris TCP |
| --- | --- | --- | --- |
| Separar cálculos ou decisões repetidos em funções diretas, chamadas pelo fluxo principal. | Em `src/calculator.js`, `89945ee` extrai `doOperation(operation)` e os handlers a chamam; em `WeekDays.tsx`, `8e5f24b` usa `daysInMonth`, `formatWeek` e `createWeek` para compor `getWeek`. | **Média**: aparece em dois repositórios, mas linguagens distintas. | Usar funções pequenas para validar payload, interpretar frames e aplicar transições da partida. Manter a sequência principal legível; evitar camadas genéricas sem uso concreto. |
| Expressar o estado com poucos valores explícitos e ramificações visíveis. | `src/calculator.js`, `89945ee`, adiciona `firstNumber`, `num1`, `num2`, `op` e usa `if`/`switch`; `js/fase1.js`, `d4019f8`, verifica a resposta com `if`/`else`. | **Média** para fluxo explícito; **baixa** para a escolha de representação do estado, pois os exemplos são pequenos. | Tornar fases e ações permitidas explícitas no cliente e servidor. Usar o menor conjunto de estados que represente corretamente a partida; testar transições e duplicações. Não copiar variáveis globais do código antigo. |
| Organizar código por função do produto quando a área cresce. | `8e5f24b` coloca cálculo de semana em `src/classes/WeekDays/WeekDays.tsx` e interface em `src/components/WeeklyDiary/index.tsx`; `d4019f8` separa `js/fase1.js`, `fase1.html` e `css/style.css`. | **Média-baixa**: a estrutura também depende dos frameworks e do tamanho dos projetos. | Conservar os módulos já existentes para protocolo, transporte, estado e interface. Extrair apenas responsabilidades que criem uma fronteira útil; preservar a estrutura atual do projeto. |
| Usar texto de interface em português para a experiência principal. | `d4019f8` usa `Resposta`, `Errou!` e `enviar` em `fase1.html`/`js/fase1.js`; `6fcef56` inclui `Fases`, `Voltar` e `Nos dê seu feedback`; `8e5f24b` usa `Faça login na sua conta` e `Entrar` em `loginScreen.tsx`. | **Alta** para textos voltados ao usuário brasileiro; os projetos web também contêm páginas em inglês. | Mensagens visíveis de espera, erro, desconexão e resultado em português. Os nomes dos oito tipos do protocolo continuam em inglês por compatibilidade. |
| Nomear operações de modo descritivo, respeitando o contexto local. | `src/calculator.js` usa `doOperation`, `operation`, `firstNumber`; `WeekDays.tsx` usa `formatWeek`, `createWeek`; `js/fase1.js` usa `verificar` e `resposta`. | **Baixa** para idioma obrigatório ou convenção exata: os identificadores misturam inglês e português. | Seguir os nomes já usados nos módulos Python e no contrato. Priorizar nomes que revelem a ação e os dados, sem renomeação geral por estética. |

## Limites da inferência

- **Python não está representado por código elegível nesta amostra histórica; a comparação recente está na seção adicional abaixo.** Portanto, não há evidência histórica para impor formato Python, tipagem, exceções, docstrings ou padrão de classes. As convenções do repositório Tetris e sua documentação prevalecem nesses pontos.
- Os exemplos de 2022 são pequenos e a interface web condiciona parte da organização. O commit de 2024 do Belifter adiciona muitos arquivos de uma vez; o Git confirma quem registrou a mudança, mas não prova autoria individual de todas as linhas enviadas. Arquivos preexistentes ao diff e dependências não foram atribuídos a Julio.
- O repositório preferido [`HigorMauricio/buscador-lexicografico`](https://github.com/HigorMauricio/buscador-lexicografico) foi excluído: sua consulta de commits até 2024-10-08 retornou vazia. Um repositório mais recente não satisfaz o corte temporal.
- As amostras variam no uso de ponto e vírgula, aspas, recuo, idioma dos identificadores, comentários e tratamento de erro. Não há base para transformar essas ocorrências em regras pessoais. Falhas antigas (por exemplo, tratamento de erros incompleto ou estado global) não devem ser reproduzidas. No Tetris TCP, integridade do protocolo, requisitos do projeto e segurança de recursos têm prioridade sobre semelhança estética.

## Revalidação das fontes nesta execução

Em 08/10/2026, um agente independente consultou novamente pelo conector GitHub os metadados, diffs e arquivos nos SHAs históricos de EcstasyRiddle (`d4019f8` e `6fcef56`), CalculadoraMaria (`89945ee`, `a430a5f` e `04d4af8`) e Belifter (`8e5f24b`). As datas, o login de autoria `JulipoDom` e os padrões da tabela foram reconfirmados. O arquivo `src/calculator.js` também foi lido no próprio SHA `89945ee`, além da versão posterior citada na tabela.

A consulta atual retornou nome civil e email como campos nulos; esses dados da análise anterior não foram reconfirmados. A ausência de commits antigos no buscador-lexicografico também não foi reconferida nesta execução. O commit do Belifter continua sendo uma importação em lote: o login do autor confirma a atribuição do commit, mas não prova autoria individual de todas as linhas. Não houve refatoração global nem imposição de convenções Python sem evidência.


## Aplicação na refatoração de menu e jogadas

Nesta etapa foram reutilizadas as evidências já registradas acima, sem nova
consulta histórica ou alegação de estilo Python comprovado. Avaliação de
limpeza, rotação, finalização, configuração e navegação ficaram em funções
diretas com responsabilidades explícitas. Comentários e docstrings novos
estão em português; nomes de APIs existentes e do TVP/1 foram preservados.
No servidor, despacho e registro foram separados sem funções anônimas para
cada comando, e validação da fase ativa foi centralizada.

## Comparação adicional com projetos Python (08/10/2026)

Estas referências são de 2026 e **não** atendem ao corte histórico de dois
anos acima. Foram consultados arquivos, histórico específico e diffs pelo
conector GitHub, atendendo ao pedido de comparação com projetos Python.
O login JulipoDom atribui os commits; não comprova autoria manual de toda linha.
Repositórios privados exigem acesso para abrir os links.

| Referência e SHA | Data UTC | Evidência e comparação |
| --- | --- | --- |
| [Aulas-Python, b91bdcb](https://github.com/JulipoDom/Aulas-Python/commit/b91bdcb9f2d8bf549e21b052b54dbd14f5c916f1) | 2026-01-19 | Diff adiciona basic-programing-logic/indentation-and-blocks.py, operators.py e Sequencial-Structures.py. Exercícios diretos, comentários em português, nomes como nome/resposta, if/loops/compreensões, sem classes ou anotações na amostra. Confiança limitada para arquitetura por serem exercícios. |
| [Python-ETL-Pratice, 7891c62](https://github.com/JulipoDom/Python-ETL-Pratice/blob/7891c622c193612d9133023784506514fc306afd/main.py) | 2026-01-20 | Commit inicial atribuído a JulipoDom. main.py contém get_anime, get_ai_news e post_anime, variáveis em português, dicionários e fluxo sequencial; funções sem anotações. Confiança média para esse arquivo, baixa para regra geral de estilo. |
| [IC-Estatistic-Modeling, 75c6382](https://github.com/JulipoDom/IC-Estatistic-Modeling/commit/75c638253cbb887953719e7a00c1e5b034206cde) | 2026-08-25 | Diff e arquivos analise.py, gui_app.py e bioherbicidas_engine.py mostram separação interface/motor, classes de UI, funções tipadas, docstrings e mensagens em português. Motor concentra muitas funções em módulo grande. Confiança média para os padrões amostrados. |

A semelhança é parcial: funções descritivas, ramificações visíveis, listas e
dicionários, comentários em português e separação interface/motor aparecem
nos projetos e no Tetris. Tipagem e classes já aparecem no projeto IC.
O Tetris usa mais Enum, dataclass, eventos imutáveis, Protocol, relógios/RNGs
injetáveis e módulos menores. Predomina inglês nos símbolos do Tetris,
enquanto as referências misturam idiomas. Não há base para afirmar que todo
o código reproduz exatamente uma assinatura pessoal, nem para refatoração
cosmética global. Correção do jogo e protocolo continuam prioritários.
