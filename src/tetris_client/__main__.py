import argparse
import logging
from pathlib import Path
import sys

from .network import NetworkSession
from .session import validate_nickname


# Lê argumentos, abre o menu padrão e informa falhas de execução.
def main() -> int:
    parser = argparse.ArgumentParser(description="Tetris Versus: treino e simulação local")
    parser.add_argument("--mode", choices=("local", "simulated", "network"),
                        help="Sem este argumento, exibir menu")
    parser.add_argument("--nickname", default="Jogador", help="Apelido ASCII de 1 a 20 caracteres")
    args = parser.parse_args()
    try:
        validate_nickname(args.nickname)
    except ValueError as exc:
        parser.error(str(exc))
    # Fail before touching the terminal; network never falls back to simulation.
    if args.mode == "network":
        try:
            NetworkSession().start(args.nickname)
        except NotImplementedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("A interface requer um terminal interativo (Linux/WSL).", file=sys.stderr)
        return 1
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(filename="logs/tetris-client.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        from .ui import run
        run(args.mode, args.nickname)
    except NotImplementedError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Falha no cliente: {exc}. Consulte logs/tetris-client.log.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
