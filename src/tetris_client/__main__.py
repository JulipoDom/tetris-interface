import argparse
import logging
from pathlib import Path
import sys

from .network import DEFAULT_HOST, DEFAULT_PORT
from .session import validate_nickname


# Lê argumentos, abre o menu padrão e informa falhas de execução.
def main() -> int:
    parser = argparse.ArgumentParser(description="Tetris Versus: treino, simulação e multiplayer TCP")
    parser.add_argument("--mode", choices=("local", "simulated", "network"),
                        help="Sem este argumento, exibir menu")
    parser.add_argument("--nickname", default="Jogador", help="Apelido ASCII de 1 a 20 caracteres")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Endereço do servidor TCP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta do servidor TCP")
    parser.add_argument("--no-timeout", action="store_true",
                        help="Desativa a derrota por 20 segundos sem teclas")
    args = parser.parse_args()
    try:
        validate_nickname(args.nickname)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.host or not 1 <= args.port <= 65535:
        parser.error("Servidor exige endereço e porta entre 1 e 65535")
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("A interface requer um terminal interativo (Linux/WSL).", file=sys.stderr)
        return 1
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(filename="logs/tetris-client.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        from .ui import run
        run(args.mode, args.nickname, host=args.host, port=args.port,
            no_timeout=args.no_timeout)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Falha no cliente: {exc}. Consulte logs/tetris-client.log.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
