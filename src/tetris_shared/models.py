from dataclasses import dataclass
from enum import Enum, IntEnum

from .rules import HEIGHT, WIDTH


class MessageType(str, Enum):
    HELLO = "HELLO"
    MATCH = "MATCH"
    READY = "READY"
    BOARD = "BOARD"
    ATTACK = "ATTACK"
    KO = "KO"
    GAMEOVER = "GAMEOVER"
    KEEPALIVE = "KEEPALIVE"


class PieceKind(IntEnum):
    I = 1
    O = 2
    T = 3
    S = 4
    Z = 5
    J = 6
    L = 7


class LossReason(str, Enum):
    SPAWN = "SPAWN"
    OVERFLOW = "OVERFLOW"


class Result(str, Enum):
    WIN = "WIN"
    LOSE = "LOSE"
    CANCEL = "CANCEL"


class EndReason(str, Enum):
    KO = "KO"
    DISCONNECT = "DISCONNECT"
    TIMEOUT = "TIMEOUT"
    PROTOCOL = "PROTOCOL"
    SERVER_STOP = "SERVER_STOP"


@dataclass(frozen=True)
class BoardSnapshot:
    cells: tuple[tuple[int, ...], ...]

    # Valida o tamanho e as células, copiando os dados recebidos.
    def __post_init__(self) -> None:
        # Sempre copia as listas de quem chamou, incluindo as linhas.
        rows = tuple(tuple(row) for row in self.cells)
        if len(rows) != HEIGHT or any(len(row) != WIDTH for row in rows):
            raise ValueError("O tabuleiro deve ter 10 colunas e 20 linhas")
        if any(type(cell) is not int or not 0 <= cell <= 8
               for row in rows for cell in row):
            raise ValueError("Células devem ser inteiros entre 0 e 8")
        object.__setattr__(self, "cells", rows)


@dataclass(frozen=True)
class AttackProduced:
    amount: int


@dataclass(frozen=True)
class BoardProduced:
    board: BoardSnapshot


@dataclass(frozen=True)
class LocalDefeat:
    reason: LossReason


EngineEvent = AttackProduced | BoardProduced | LocalDefeat


@dataclass(frozen=True)
class OpponentDefined:
    nickname: str


@dataclass(frozen=True)
class StartAuthorized:
    pass


@dataclass(frozen=True)
class BoardReceived:
    board: BoardSnapshot


@dataclass(frozen=True)
class AttackReceived:
    amount: int


@dataclass(frozen=True)
class MatchResult:
    result: Result
    reason: EndReason


@dataclass(frozen=True)
class ConnectionLost:
    detail: str = "Partida interrompida; resultado não confirmado"


SessionEvent = (OpponentDefined | StartAuthorized | BoardReceived |
                AttackReceived | MatchResult | ConnectionLost)
