# Superpowers neste projeto

As 15 skills oficiais de [obra/superpowers](https://github.com/obra/superpowers)
estão incluídas em `skills/`, sem alterações, na revisão
`8ca22dba9a94f28898bbce59f2537ff4d87c747d`. Licença MIT em `LICENSE`.
Instalação feita pelo helper oficial `skill-installer` do Codex em 04/10/2026.
`provenance.json` registra origem, revisão e hashes SHA-256 dos arquivos.

O [AGENTS.md](../AGENTS.md) determina a leitura de `using-superpowers` no
início de cada tarefa e das demais skills quando aplicáveis. A configuração
vale para as tarefas deste projeto; não altera a
configuração global da máquina. Quando não houver ferramenta Skill, o agente
deve ler o arquivo local diretamente.

Nesta sessão `.agents/` e `.codex/` são diretórios reservados somente para
leitura. Por isso os arquivos ficam em `.superpowers/`, e sua ativação padrão
usa `AGENTS.md`, sem depender da descoberta nativa ou de um bootstrap antigo.

Para descoberta nativa em um checkout onde `.agents/` seja gravável, execute
na raiz do projeto:

```bash
mkdir -p .agents/skills
ln -s ../../.superpowers/skills .agents/skills/superpowers
```

Depois abra uma nova sessão do agente para atualizar o catálogo. Não substitua
um link/diretório existente sem verificar seu destino. Mesmo sem esse link,
as instruções de carregamento direto em `AGENTS.md` continuam válidas.

Para atualizar, escolha uma revisão oficial, reinstale as skills com
`install-skill-from-github.py --repo obra/superpowers --ref <revisão>
--dest <diretório-temporário> --path skills/<nome> ...`, revise as diferenças,
substitua os arquivos deliberadamente e atualize licença, revisão e hashes.
O instalador recusa sobrescrever skills existentes.
