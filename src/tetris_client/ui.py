"""Toda chamada curses ocorre no fluxo principal e dentro da função curses.wrapper."""

import curses
import logging

from tetris_shared.models import EndReason, MatchResult, Result
from tetris_shared.rules import MIN_TERMINAL_HEIGHT, MIN_TERMINAL_WIDTH
from .app import App, State
from .engine import SHAPES
from .network import DEFAULT_HOST, DEFAULT_PORT, NetworkSession
from .session import FakeSession, validate_nickname


# Desenha texto dentro dos limites disponíveis do terminal.
def _text(screen, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = screen.getmaxyx()
    if 0 <= y < height and 0 <= x < width - 1:
        try:
            screen.addnstr(y, x, text, width - x - 1, attr)
        except curses.error:
            # O redimensionamento pode coincidir com o desenho. O próximo quadro usa o novo tamanho.
            pass


# Prepara cores de peças com alternativa monocromática.
def _palette() -> dict[int, int]:
    palette = {i: 0 for i in range(9)}
    if curses.has_colors():
        try:
            curses.start_color()
            background = curses.COLOR_BLACK
            try:
                curses.use_default_colors()
                background = -1
            except curses.error:
                pass
            colors = (curses.COLOR_CYAN, curses.COLOR_YELLOW, curses.COLOR_MAGENTA,
                      curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_BLUE,
                      curses.COLOR_WHITE, curses.COLOR_WHITE)
            for index, color in enumerate(colors, 1):
                if index < curses.COLOR_PAIRS:
                    curses.init_pair(index, color, background)
                    palette[index] = curses.color_pair(index) | curses.A_BOLD
        except curses.error:
            return {i: 0 for i in range(9)}
    return palette


# Desenha uma cópia do tabuleiro com a peça ativa sobreposta.
def _board(screen, x: int, rows, palette: dict[int, int], active=None) -> None:
    projection = [list(row) for row in rows]
    if active:
        for px, py in active.occupied():
            projection[py][px] = int(active.kind)
    _text(screen, 4, x, "+" + "-" * 20 + "+")
    for y, row in enumerate(projection, 5):
        _text(screen, y, x, "|")
        for col, value in enumerate(row):
            _text(screen, y, x + 1 + col * 2, "[]" if value else "  ", palette[value])
        _text(screen, y, x + 21, "|")
    _text(screen, 25, x, "+" + "-" * 20 + "+")


# Desenha nomes, estado da partida, tabuleiros e informações locais.
def _render(screen, app: App, palette: dict[int, int]) -> None:
    screen.erase()
    _text(screen, 0, 2, "TETRIS VERSUS", curses.A_BOLD)
    if app.mode == "simulated":
        _text(screen, 1, 2, "SIMULAÇÃO LOCAL - SEM REDE", curses.A_BOLD)
    elif app.mode == "local":
        _text(screen, 1, 2, "TREINO LOCAL")
    statuses = {
        State.WAITING: "Aguardando outro jogador",
        State.PREPARING: "Enter para ficar pronto",
        State.READY: "Pronto; aguardando autorização de início",
        State.PLAYING: "PAUSADO" if app.paused else "Jogando",
        State.AWAITING_RESULT: "Derrota local; aguardando resultado confirmado",
        State.FINISHED: app.notice,
        State.INTERRUPTED: app.notice,
    }
    _text(screen, 2, 2, statuses.get(app.state, "Menu"))
    height, width = screen.getmaxyx()
    if height < MIN_TERMINAL_HEIGHT or width < MIN_TERMINAL_WIDTH:
        _text(screen, 4, 0, "Terminal pequeno: aumente para pelo menos 80x28. q sai.")
        screen.refresh()
        return
    _text(screen, 3, 2, f"Você: {app.nickname}")
    _board(screen, 2, app.engine.board, palette, app.engine.active)
    if app.mode != "local":
        _text(screen, 3, 28, app.opponent or "Aguardando jogador")
    if app.remote_board:
        _board(screen, 28, app.remote_board.cells, palette)
    elif app.mode != "local":
        _text(screen, 7, 28, "Aguardando tabuleiro")
        _text(screen, 8, 28, "do oponente")
    _text(screen, 5, 53, f"Score: {app.engine.score}")
    _text(screen, 7, 53, f"Lixo pendente: {app.engine.pending_garbage}")
    _text(screen, 8, 53, f"Fixação: {app.engine.lock_delay * 1000:.0f} ms")
    kind = app.engine.next_kind
    _text(screen, 9, 53, f"Próxima: {kind.name}")
    for x, y in SHAPES[kind][1]:
        _text(screen, 11 + y, 53 + x * 2, "[]", palette[int(kind)])
    held = app.engine.held_kind
    _text(screen, 15, 53, f"Guardada: {held.name if held is not None else 'vazia'}")
    if held is not None:
        for x, y in SHAPES[held][1]:
            _text(screen, 17 + y, 53 + x * 2, "[]", palette[int(held)])
    if app.mode == "simulated":
        _text(screen, 22, 53, "Demo: v = vitória")
        _text(screen, 23, 53, "b = cancelamento")
        _text(screen, 24, 53, "d = desconexão")
    _text(screen, 26, 2, "Setas: mover/girar/descer | Espaço: queda | Enter: pronto | q: sair")
    controls = "Z: anti-horário | X: horário | A: 180° | C: guardar"
    if app.mode == "local":
        controls += " | p: pausar"
    _text(screen, 27, 2, controls)
    screen.refresh()


# Permite escolher treino ou modo multijogador e editar o apelido.
def _menu(screen, initial_nickname: str, error: str = "") -> tuple[str, str] | None:
    nickname = initial_nickname
    mode_index = 0
    modes = ("local", "network")
    labels = ("Prática", "Multiplayer")
    while True:
        screen.erase()
        _text(screen, 1, 2, "TETRIS VERSUS", curses.A_BOLD)
        _text(screen, 3, 2, "Cima/baixo: modo | Digite o apelido | Enter: iniciar | Esc: sair")
        for i, label in enumerate(labels):
            _text(screen, 5 + i, 2, ("> " if i == mode_index else "  ") + label)
        _text(screen, 10, 2, f"Apelido: {nickname}")
        _text(screen, 11, 2, "Multiplayer: indisponível até a implementação da rede.")
        _text(screen, 12, 2, error)
        screen.refresh()
        key = screen.getch()
        if key == 27:
            return None
        if key == curses.KEY_UP:
            mode_index = (mode_index - 1) % len(modes)
        elif key == curses.KEY_DOWN:
            mode_index = (mode_index + 1) % len(modes)
        elif key in (10, 13, curses.KEY_ENTER):
            try:
                validate_nickname(nickname)
            except ValueError as exc:
                error = str(exc)
            else:
                return modes[mode_index], nickname
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            nickname = nickname[:-1]
        elif 0 <= key < 128 and (chr(key).isalnum() or key == ord("_")):
            if len(nickname) < 20:
                nickname += chr(key)


# Coordena menu, entrada de teclado e atualizações no mesmo fluxo.
def _run(screen, mode: str | None, nickname: str, *,
         host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True)
    screen.timeout(33)
    palette = _palette()
    from_menu = mode is None
    menu_error = ""
    while True:
        if from_menu:
            choice = _menu(screen, nickname, menu_error)
            if choice is None:
                return
            mode, nickname = choice
        session = (FakeSession(demo=True) if mode == "simulated" else
                   NetworkSession(host, port) if mode == "network" else None)
        app = App(mode, nickname, session=session)
        try:
            app.start()
        except Exception as exc:
            app.close()
            if not isinstance(exc, NotImplementedError) or not from_menu:
                raise
            menu_error = "Multiplayer indisponível: implemente os pontos TODO[EP-REDE]."
            continue
        break
    keys = {curses.KEY_LEFT: "left", curses.KEY_RIGHT: "right",
            curses.KEY_DOWN: "down", curses.KEY_UP: "rotate", ord(" "): "drop",
            10: "ready", 13: "ready", curses.KEY_ENTER: "ready", ord("p"): "pause"}
    for key, action in (("z", "rotate_ccw"), ("x", "rotate"),
                        ("a", "rotate_180"), ("c", "hold")):
        keys[ord(key)] = keys[ord(key.upper())] = action
    try:
        while True:
            app.update()
            _render(screen, app, palette)
            key = screen.getch()
            if key == ord("q"):
                return
            if isinstance(session, FakeSession) and app.state not in (
                State.FINISHED, State.INTERRUPTED,
            ):
                if key == ord("d"):
                    session.simulate_disconnect()
                elif key in (ord("b"), ord("B")):
                    session.simulate_cancel()
                elif key == ord("v") and app.state == State.PLAYING:
                    session.inject(MatchResult(Result.WIN, EndReason.KO))
            if key in keys:
                app.action(keys[key])
    finally:
        app.close()


# Executa a interface restaurando o terminal mesmo quando ocorre erro.
def run(mode: str | None, nickname: str, *,
        host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    try:
        curses.wrapper(_run, mode, nickname, host=host, port=port)
    except Exception:
        logging.exception("Falha no cliente")
        raise
