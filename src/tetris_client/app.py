"""Coordenação testável sem curses; rede pertence somente à porta de sessão."""

from enum import Enum

from tetris_shared.models import (
    AttackProduced, AttackReceived, BoardProduced, BoardReceived, BoardSnapshot,
    ConnectionLost, EngineEvent, LocalDefeat, MatchResult, OpponentDefined,
    StartAuthorized,
)
from .engine import Engine, GarbageLimitError
from .session import Session, validate_nickname


class State(str, Enum):
    MENU = "menu"
    WAITING = "waiting"
    PREPARING = "preparing"
    READY = "ready"
    PLAYING = "playing"
    AWAITING_RESULT = "awaiting_result"
    FINISHED = "finished"
    INTERRUPTED = "interrupted"


class App:
    # Prepara o estado da aplicação com um motor e uma sessão opcional.
    def __init__(self, mode: str, nickname: str, *, engine: Engine | None = None,
                 session: Session | None = None) -> None:
        if mode not in ("local", "simulated", "network"):
            raise ValueError("Modo desconhecido")
        if mode != "local" and session is None:
            raise ValueError("Modo de sessão exige uma porta explícita")
        validate_nickname(nickname)
        self.mode = mode
        self.nickname = nickname
        self.engine = engine if engine is not None else Engine()
        self.session = session
        self.state = State.MENU
        self.opponent: str | None = None
        self.remote_board: BoardSnapshot | None = None
        self.result: MatchResult | None = None
        self.notice = ""
        self.paused = False
        self.closed = False

    # Inicia o treino ou abre uma sessão usando o apelido escolhido.
    def start(self) -> None:
        if self.state != State.MENU:
            return
        if self.mode == "local":
            self.state = State.PLAYING
            self._publish(self.engine.start())
        else:
            self.state = State.WAITING
            assert self.session is not None
            self.session.start(self.nickname)

    # Confirma prontidão sem iniciar a física antes da autorização.
    def ready(self) -> None:
        if self.state == State.PREPARING:
            assert self.session is not None
            self.session.ready()
            self.state = State.READY

    # Encaminha ocorrências do motor preservando ataque, tabuleiro e derrota.
    def _publish(self, events: list[EngineEvent]) -> None:
        for event in events:
            if isinstance(event, AttackProduced):
                if self.session:
                    self.session.attack(event.amount)
            elif isinstance(event, BoardProduced):
                if self.session:
                    self.session.offer_board(event.board)
            elif isinstance(event, LocalDefeat):
                if self.session:
                    self.session.defeat(event.reason)
                    self.state = State.AWAITING_RESULT
                else:
                    self.state = State.FINISHED
                    self.notice = "Fim do treino"

    # Consome eventos da sessão e atualiza o motor quando o jogo está ativo.
    def update(self) -> None:
        if self.closed or self.state in (State.FINISHED, State.INTERRUPTED):
            return
        if self.session:
            for event in self.session.poll():
                if self.state in (State.FINISHED, State.INTERRUPTED):
                    break
                if isinstance(event, OpponentDefined) and self.state == State.WAITING:
                    self.opponent = event.nickname
                    self.state = State.PREPARING
                elif isinstance(event, StartAuthorized) and self.state == State.READY:
                    self.state = State.PLAYING
                    self._publish(self.engine.start())
                elif isinstance(event, BoardReceived) and self.state in (
                    State.PLAYING, State.AWAITING_RESULT,
                ):
                    self.remote_board = BoardSnapshot(event.board.cells)
                elif isinstance(event, AttackReceived) and self.state == State.PLAYING:
                    try:
                        self.engine.receive_garbage(event.amount)
                    except GarbageLimitError as exc:
                        self._interrupt(f"{exc}; resultado não confirmado")
                elif isinstance(event, MatchResult):
                    self.result = event
                    self.state = State.FINISHED
                    self.engine.stop()
                    self.notice = f"Resultado confirmado: {event.result.value} / {event.reason.value}"
                    self.session.close()
                elif isinstance(event, ConnectionLost):
                    self._interrupt(event.detail)
        if self.state == State.PLAYING and not self.paused:
            self._publish(self.engine.tick())

    # Traduz uma ação do jogador em movimento, prontidão ou pausa local.
    def action(self, action: str) -> None:
        if action == "ready":
            self.ready()
            return
        if self.state != State.PLAYING:
            return
        if action == "pause" and self.mode == "local":
            self.paused = not self.paused
            if self.paused:
                self.engine.pause()
            else:
                self.engine.resume()
            return
        if self.paused:
            return
        if action == "left":
            self.engine.move(-1)
        elif action == "right":
            self.engine.move(1)
        elif action == "rotate":
            self.engine.rotate()
        elif action == "rotate_ccw":
            self.engine.rotate(-1)
        elif action == "rotate_180":
            self.engine.rotate(2)
        elif action == "hold":
            self._publish(self.engine.hold())
        elif action == "down":
            self._publish(self.engine.soft_drop())
        elif action == "drop":
            self._publish(self.engine.hard_drop())

    # Para o jogo e fecha a sessão sem inventar um resultado.
    def _interrupt(self, detail: str) -> None:
        self.notice = detail
        self.state = State.INTERRUPTED
        self.engine.stop()
        if self.session:
            self.session.close()

    # Encerra a aplicação e libera a sessão uma única vez.
    def close(self) -> None:
        if self.closed:
            return
        self.engine.stop()
        if self.session:
            self.session.close()
        self.closed = True
