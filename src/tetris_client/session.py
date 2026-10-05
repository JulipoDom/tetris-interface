"""Porta tipada e sessão simulada: objetos Python, sem bytes, arquivos ou rede."""

import re
from collections import deque
from dataclasses import dataclass
from typing import Protocol

from tetris_shared.models import (
    AttackReceived, BoardReceived, BoardSnapshot, ConnectionLost, EndReason,
    LossReason, MatchResult, OpponentDefined, Result, SessionEvent, StartAuthorized,
)
from tetris_shared.rules import HEIGHT, WIDTH


# Valida o apelido ASCII que será usado em HELLO.
def validate_nickname(nickname: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9_]{1,20}", nickname) is None:
        raise ValueError("Apelido: 1 a 20 letras ASCII, números ou underscore")


class Session(Protocol):
    # Abre a sessão com o apelido que corresponde ao futuro HELLO.
    def start(self, nickname: str) -> None: ...
    # Registra prontidão; a sessão simulada agenda uma autorização separada.
    def ready(self) -> None: ...
    # Oferece uma cópia dos blocos fixos para envio ao oponente.
    def offer_board(self, board: BoardSnapshot) -> None: ...
    # Informa a quantidade de lixo produzida pela jogada local.
    def attack(self, amount: int) -> None: ...
    # Informa a derrota local e aguarda a confirmação da partida.
    def defeat(self, reason: LossReason) -> None: ...
    # Fecha a sessão e encerra o processamento de suas entradas.
    def close(self) -> None: ...
    # Retorna os eventos disponíveis sem bloquear a aplicação.
    def poll(self) -> list[SessionEvent]: ...


@dataclass(frozen=True)
class HelloOffered:
    nickname: str


@dataclass(frozen=True)
class ReadyOffered:
    pass


@dataclass(frozen=True)
class BoardOffered:
    board: BoardSnapshot


@dataclass(frozen=True)
class AttackOffered:
    amount: int


@dataclass(frozen=True)
class DefeatOffered:
    reason: LossReason


SessionOutput = HelloOffered | ReadyOffered | BoardOffered | AttackOffered | DefeatOffered


class FakeSession:
    """Injeção manual para testes; roteiro demonstrativo opcional na interface de terminal.

    Uma consulta retorna um lote. READY registra a saída e agenda GO para
    outra consulta. demo não representa um segundo motor nem um servidor.
    """

    # Cria filas de eventos e registros da sessão simulada.
    def __init__(self, *, demo: bool = False) -> None:
        self.demo = demo
        self.outgoing: list[SessionOutput] = []
        self._incoming: deque[list[SessionEvent]] = deque()
        self.started = False
        self.ready_sent = False
        self.closed = False
        self._demo_boards = 0

    # Agenda um lote de eventos internos sem usar comunicação externa.
    def inject(self, *events: SessionEvent) -> None:
        if not self.closed:
            self._incoming.append(list(events))

    # Abre a sessão com o apelido que corresponde ao futuro HELLO.
    def start(self, nickname: str) -> None:
        validate_nickname(nickname)
        if self.started or self.closed:
            raise RuntimeError("A sessão não pode ser reutilizada")
        self.started = True
        self.outgoing.append(HelloOffered(nickname))
        if self.demo:
            self.inject()  # Um ciclo de espera observável.
            self.inject(OpponentDefined("Oponente_demo"))

    # Registra prontidão; a sessão simulada agenda uma autorização separada.
    def ready(self) -> None:
        if not self.started or self.closed:
            raise RuntimeError("Sessão não está aberta")
        if not self.ready_sent:
            self.ready_sent = True
            self.outgoing.append(ReadyOffered())
            if self.demo:
                self.inject()
                self.inject(StartAuthorized())

    # Oferece uma cópia dos blocos fixos para envio ao oponente.
    def offer_board(self, board: BoardSnapshot) -> None:
        self.outgoing.append(BoardOffered(BoardSnapshot(board.cells)))
        if self.demo:
            self._demo_boards += 1
            if self._demo_boards == 1:
                rows = [[0] * WIDTH for _ in range(HEIGHT)]
                rows[-1] = [8] * WIDTH
                rows[-1][4] = 0
                self.inject(BoardReceived(BoardSnapshot(rows)))
            elif self._demo_boards % 5 == 0:
                self.inject(AttackReceived(1))

    # Informa a quantidade de lixo produzida pela jogada local.
    def attack(self, amount: int) -> None:
        if type(amount) is not int or amount not in (1, 2, 4):
            raise ValueError("Ataque inválido")
        self.outgoing.append(AttackOffered(amount))

    # Informa a derrota local e aguarda a confirmação da partida.
    def defeat(self, reason: LossReason) -> None:
        self.outgoing.append(DefeatOffered(reason))
        if self.demo:
            self.inject(MatchResult(Result.LOSE, EndReason.KO))

    # Fecha a sessão e encerra o processamento de suas entradas.
    def close(self) -> None:
        self.closed = True
        self._incoming.clear()

    # Retorna os eventos disponíveis sem bloquear a aplicação.
    def poll(self) -> list[SessionEvent]:
        if self.closed or not self._incoming:
            return []
        return self._incoming.popleft()

    # Agenda uma perda de conexão para demonstração local.
    def simulate_disconnect(self) -> None:
        self.inject(ConnectionLost())

    # Agenda um cancelamento confirmado para demonstração local.
    def simulate_cancel(self) -> None:
        self.inject(MatchResult(Result.CANCEL, EndReason.SERVER_STOP))
