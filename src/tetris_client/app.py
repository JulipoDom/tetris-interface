"""Coordenação testável sem curses; rede pertence somente à porta de sessão."""

from enum import Enum
from collections.abc import Callable
import math
import time

from tetris_shared.models import (
    AttackProduced, AttackReceived, BoardProduced, BoardReceived, BoardSnapshot,
    ConnectionLost, EndReason, EngineEvent, LocalDefeat, MatchResult,
    LossReason, OpponentDefined, Result, StartAuthorized,
)
from .engine import Engine, GarbageLimitError
from .session import Session, validate_nickname


# O terminal não envia soltura da tecla; silêncio entre entradas libera o drop.
HARD_DROP_RELEASE_SECONDS = 0.6


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
                 session: Session | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 no_timeout: bool = False) -> None:
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
        self._clock = clock
        # A opção acompanha a aplicação, inclusive quando o motor é reiniciado.
        self.no_timeout = no_timeout
        self._last_input = clock()
        self._last_drop_input: float | None = None
        self._finished_at: float | None = None
        self.rematch_requested = False

    @property
    def rematch_seconds(self) -> int:
        """Mostra o prazo restante sem reiniciá-lo ao pressionar uma tecla."""
        if self._finished_at is None:
            return 0
        return max(0, math.ceil(10 - (self._clock() - self._finished_at)))

    def record_input(self) -> None:
        """Qualquer tecla durante a partida renova a atividade do jogador."""
        if self.state == State.PLAYING:
            self._last_input = self._clock()

    def request_rematch(self) -> None:
        """Solicita nova rodada; a física aguarda o acordo dos dois jogadores."""
        if self.state != State.FINISHED or self.rematch_requested or self.rematch_seconds == 0:
            return
        self.rematch_requested = True
        if self.session:
            self.session.rematch()
        else:
            self._restart()

    def _restart(self) -> None:
        """Zera o motor e os temporizadores conservando a dupla e a sessão."""
        self.engine = Engine(clock=self._clock)
        self.remote_board = None
        self.result = None
        self.notice = ''
        self.paused = False
        self.rematch_requested = False
        self._finished_at = None
        self._last_input = self._clock()
        self.state = State.PLAYING
        self._publish(self.engine.start())

    @property
    def winner(self) -> str | None:
        """Deriva o vencedor somente de um resultado confirmado pelo servidor."""
        if self.result is None or self.result.result == Result.CANCEL:
            return None
        return self.nickname if self.result.result == Result.WIN else self.opponent

    # Guarda o resultado e inicia o prazo de escolha sem fechar a dupla.
    def _finish_match(self, result: MatchResult) -> None:
        self.result = result
        self.state = State.FINISHED
        self._finished_at = self._clock()
        self.engine.stop()
        outcomes = {Result.WIN: "Vitória confirmada", Result.LOSE: "Derrota confirmada",
                    Result.CANCEL: "Partida cancelada"}
        reasons = {EndReason.KO: "nocaute", EndReason.DISCONNECT: "desconexão",
                   EndReason.TIMEOUT: "tempo esgotado", EndReason.PROTOCOL: "falha de protocolo",
                   EndReason.SERVER_STOP: "servidor encerrado"}
        self.notice = f"{outcomes[result.result]}: {reasons[result.reason]}"

    # Inicia o treino ou abre uma sessão usando o apelido escolhido.
    def start(self) -> None:
        if self.state != State.MENU:
            return
        if self.mode == "local":
            self.state = State.PLAYING
            self._last_input = self._clock()
            self._publish(self.engine.start())
        else:
            self.state = State.WAITING
            if self.mode == "network":
                self.notice = "Conectando ao servidor"
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
                    self._finished_at = self._clock()
                    self.notice = "Fim do treino"

    # Consome eventos da sessão e atualiza o motor quando o jogo está ativo.
    def update(self) -> None:
        if self.closed or self.state == State.INTERRUPTED:
            return
        if (self.mode == "network" and self.state == State.WAITING
                and self.session is not None and getattr(self.session, "connected", False)):
            self.notice = "Aguardando outro jogador"
        if self.session:
            for event in self.session.poll():
                if self.state == State.INTERRUPTED:
                    break
                if isinstance(event, OpponentDefined) and self.state == State.WAITING:
                    self.opponent = event.nickname
                    self.state = State.PREPARING
                elif isinstance(event, StartAuthorized) and self.state == State.READY:
                    self.state = State.PLAYING
                    self._last_input = self._clock()
                    self._publish(self.engine.start())
                elif (isinstance(event, StartAuthorized) and self.state == State.FINISHED
                      and self.rematch_requested):
                    self._restart()
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
                    if self.state != State.FINISHED:
                        self._finish_match(event)
                elif isinstance(event, ConnectionLost):
                    if self.state == State.FINISHED:
                        self.close()
                    else:
                        self._interrupt(event.detail)
        if self.state == State.FINISHED:
            if self.rematch_seconds == 0:
                self.close()
            return
        if (self.state == State.PLAYING and not self.no_timeout
                and self._clock() - self._last_input > 20):
            self.engine.stop()
            self.notice = 'Game over: mais de 20 segundos sem teclas'
            self._publish([LocalDefeat(LossReason.INACTIVITY)])
            if self.mode == 'local':
                self.notice = 'Game over: mais de 20 segundos sem teclas'
            return
        if self.state == State.PLAYING and not self.paused:
            self._publish(self.engine.tick())

    # Traduz uma ação do jogador em movimento, prontidão ou pausa local.
    def action(self, action: str) -> None:
        self.record_input()
        if action == "drop":
            now = self._clock()
            previous = self._last_drop_input
            # Repetições também renovam a trava para não derrubar a próxima peça.
            self._last_drop_input = now
            if previous is not None and now - previous < HARD_DROP_RELEASE_SECONDS:
                return
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
