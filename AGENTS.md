# Default workflow: Superpowers

For every new task in this repository, first read
`.superpowers/skills/using-superpowers/SKILL.md` and its Codex reference
`.superpowers/skills/using-superpowers/references/codex-tools.md`.
Use the relevant Superpowers skills by default; the user does not need to
mention them. Announce the skill being used and read its `SKILL.md` before
following its workflow.

The pinned skills are in `.superpowers/skills/<skill-name>/SKILL.md`.
When the harness has no Skill tool or native discovery, read these files
directly with the available file/shell tools. This is the default loading
mechanism for this checkout; do not require a global installation.

Use brainstorming for new designs, writing-plans for substantial multi-step
changes, test-driven-development for behavior changes, systematic-debugging
for defects, and verification-before-completion before reporting success.
An explicit, accepted specification can supply existing design decisions;
ask only about unresolved choices. Do not restart already completed work
merely to apply a newly installed workflow retroactively.

Direct user instructions, system/developer instructions, actual tool
availability, and workspace permissions take precedence over vendored skill
guidance. Repository setup alone does not authorize publishing, committing,
changing global configuration, or creating subagents. Apply delegation and
Git worktree skills only when authorized and supported by the environment.

## Project contract

- `00-contexto-geral.md` is the source of truth; read it with
  `01-boilerplate-interface.md` when changing game rules or architecture.
- Python 3.12+, standard library at runtime, `curses` TUI on Linux/WSL.
- `engine.py` must not import curses, socket, or session adapters.
- Two players and one match; exactly eight message types. No rooms,
  matchmaking, accounts, rankings, or match identifiers.
- Network and protocol methods remain `TODO[EP-REDE]` stubs raising
  `NotImplementedError` until real networking is explicitly requested.
  Network mode must never fall back to FakeSession.
- Preserve the existing thread/queue scaffold in `network.py`. The main thread
  owns Engine and curses; `_start_worker`, `_enqueue`, `_publish`, `poll`, and
  `close` coordinate threads and objects only. TCP, codec, framing, byte buffers,
  and network timers remain `TODO[EP-REDE]` implementation points.
- Keep comments and docstrings in project-owned Python files in Portuguese.
  Preserve official API names, identifiers, and vendored third-party sources.
- Preserve attack → board snapshot → local defeat when publishing a lock.
- Use injectable clocks and separate piece/garbage RNGs for deterministic tests.
- Run `.venv/bin/python -m unittest discover -s tests` after behavior changes.
  Without an installed environment use
  `PYTHONPATH=src python3 -m unittest discover -s tests`.
- Keep the pinned third-party skills and license intact. Record any deliberate
  update in `.superpowers/README.md` and the provenance manifest.
