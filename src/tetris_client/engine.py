"""Motor puro. A fixação é uma transação; nenhuma entrada é consultada no meio."""

import random
import time
from dataclasses import dataclass
from typing import Callable

from tetris_shared.models import (
    AttackProduced, BoardProduced, BoardSnapshot, EngineEvent, LocalDefeat,
    LossReason, PieceKind,
)
from tetris_shared.rules import (
    ATTACK_BY_LINES, GRAVITY_SECONDS, HEIGHT, INITIAL_LOCK_DELAY_SECONDS,
    LOCK_DELAY_INTERVAL_SECONDS, LOCK_DELAY_REDUCTION_SECONDS, MIN_LOCK_DELAY_SECONDS,
    MAX_CATCH_UP_STEPS,
    MAX_GARBAGE_PER_LOCK, MAX_PENDING_GARBAGE, SCORE_BY_LINES, WIDTH,
)

SHAPES = {
    PieceKind.I: (4, ((0, 1), (1, 1), (2, 1), (3, 1))),
    PieceKind.O: (2, ((0, 0), (1, 0), (0, 1), (1, 1))),
    PieceKind.T: (3, ((1, 0), (0, 1), (1, 1), (2, 1))),
    PieceKind.S: (3, ((1, 0), (2, 0), (0, 1), (1, 1))),
    PieceKind.Z: (3, ((0, 0), (1, 0), (1, 1), (2, 1))),
    PieceKind.J: (3, ((0, 0), (0, 1), (1, 1), (2, 1))),
    PieceKind.L: (3, ((2, 0), (0, 1), (1, 1), (2, 1))),
}


class GarbageLimitError(RuntimeError):
    """Falha de sessão local, nunca uma derrota do jogo."""


@dataclass(frozen=True)
class Piece:
    kind: PieceKind
    x: int
    y: int
    cells: tuple[tuple[int, int], ...]

    # Retorna as coordenadas do tabuleiro ocupadas pela peça.
    def occupied(self) -> tuple[tuple[int, int], ...]:
        return tuple((self.x + x, self.y + y) for x, y in self.cells)


class Engine:
    # Cria um jogo vazio com relógio e geradores aleatórios independentes.
    def __init__(self, *, piece_rng: random.Random | None = None,
                 garbage_rng: random.Random | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.piece_rng = piece_rng if piece_rng is not None else random.Random()
        self.garbage_rng = garbage_rng if garbage_rng is not None else random.Random()
        self.clock = clock
        self.board = [[0] * WIDTH for _ in range(HEIGHT)]
        self.score = 0
        self.pending_garbage = 0
        self.active: Piece | None = None
        self.held_kind: PieceKind | None = None
        self.hold_used = False
        self.loss: LossReason | None = None
        self.running = False
        self._has_started = False
        self._bag: list[PieceKind] = []
        self.next_kind = self._draw()
        self._last_tick = clock()
        self._started_at = self._last_tick
        self._paused_at: float | None = None
        self._lock_deadline: float | None = None

    @property
    # Calcula o atraso de fixação conforme o tempo ativo de jogo.
    def lock_delay(self) -> float:
        """Calcula a espera de fixação usando somente o tempo ativo de jogo."""
        if not self._has_started:
            return INITIAL_LOCK_DELAY_SECONDS
        now = self.clock() if self._paused_at is None else self._paused_at
        elapsed = max(0.0, now - self._started_at)
        reductions = int(elapsed / LOCK_DELAY_INTERVAL_SECONDS)
        return max(MIN_LOCK_DELAY_SECONDS,
                   INITIAL_LOCK_DELAY_SECONDS - reductions * LOCK_DELAY_REDUCTION_SECONDS)

    # Verifica se existe chão ou bloco impedindo a próxima descida.
    def _grounded(self) -> bool:
        """Verifica se a peça ativa não consegue descer mais uma linha."""
        if self.active is None:
            return False
        p = self.active
        return not self._valid(Piece(p.kind, p.x, p.y + 1, p.cells))

    # Inicia o prazo de fixação sem reiniciá-lo a cada movimento.
    def _touch_ground(self) -> None:
        """Inicia um prazo único por peça no primeiro contato com o chão."""
        if self._lock_deadline is None and self._grounded():
            self._lock_deadline = self.clock() + self.lock_delay

    # Congela o tempo do treino e o prazo da peça apoiada.
    def pause(self) -> None:
        """Congela os relógios de gravidade, dificuldade e fixação no treino."""
        if self.running and self._paused_at is None:
            self._paused_at = self.clock()

    # Retoma o treino descontando a duração da pausa dos relógios.
    def resume(self) -> None:
        """Retoma o treino preservando o tempo restante antes da fixação."""
        if self._paused_at is not None:
            now = self.clock()
            duration = now - self._paused_at
            self._started_at += duration
            if self._lock_deadline is not None:
                self._lock_deadline += duration
            self._paused_at = None
            self._last_tick = now

    # Retira a próxima peça de uma coleção embaralhada de sete peças.
    def _draw(self) -> PieceKind:
        if not self._bag:
            self._bag = list(PieceKind)
            self.piece_rng.shuffle(self._bag)
        return self._bag.pop()

    # Copia somente os blocos fixos para uma projeção imutável.
    def snapshot(self) -> BoardSnapshot:
        return BoardSnapshot(tuple(tuple(row) for row in self.board))

    # Confere os limites e as colisões de todas as células da peça.
    def _valid(self, piece: Piece) -> bool:
        return all(0 <= x < WIDTH and 0 <= y < HEIGHT and self.board[y][x] == 0
                   for x, y in piece.occupied())

    # Gera a peça seguinte e detecta derrota por nascimento bloqueado.
    def _spawn(self, kind: PieceKind | None = None) -> None:
        self._lock_deadline = None
        if kind is None:
            kind = self.next_kind
            self.next_kind = self._draw()
        size, cells = SHAPES[kind]
        piece = Piece(kind, (WIDTH - size) // 2, 0, cells)
        if self._valid(piece):
            self.active = piece
        else:
            self.active = None
            self.loss = LossReason.SPAWN
            self.running = False

    # Guarda ou troca a peça uma vez por fixação, sem alterar os blocos fixos.
    def hold(self) -> list[EngineEvent]:
        if (not self.running or self._paused_at is not None or self.active is None
                or self.hold_used):
            return []
        replacement = self.held_kind
        self.held_kind = self.active.kind
        self.hold_used = True
        self._spawn(replacement)
        self._last_tick = self.clock()
        self._touch_ground()
        if self.loss is not None:
            return [BoardProduced(self.snapshot()), LocalDefeat(self.loss)]
        return []

    # Inicia a física e produz o primeiro tabuleiro consolidado.
    def start(self) -> list[EngineEvent]:
        if self.running or self.loss is not None:
            return []
        self.running = True
        self._has_started = True
        self._last_tick = self.clock()
        self._started_at = self._last_tick
        self._paused_at = None
        self._spawn()
        events: list[EngineEvent] = [BoardProduced(self.snapshot())]
        if self.loss is not None:
            events.append(LocalDefeat(self.loss))
        return events

    # Interrompe a física sem produzir um resultado multijogador.
    def stop(self) -> None:
        self.running = False

    # Reinicia o relógio da gravidade sem alterar o tabuleiro.
    def reset_time(self) -> None:
        self._last_tick = self.clock()

    # Acumula lixo válido e interrompe entradas acima do limite.
    def receive_garbage(self, amount: int) -> None:
        if type(amount) is not int or amount not in (1, 2, 4):
            raise ValueError("ATTACK deve informar 1, 2 ou 4 linhas de lixo")
        if self.pending_garbage + amount > MAX_PENDING_GARBAGE:
            raise GarbageLimitError("Limite de 40 linhas pendentes excedido")
        self.pending_garbage += amount

    # Move a peça na horizontal somente se a posição for válida.
    def move(self, dx: int) -> None:
        if self.running and self._paused_at is None and self.active:
            p = self.active
            candidate = Piece(p.kind, p.x + dx, p.y, p.cells)
            if self._valid(candidate):
                self.active = candidate
                self._touch_ground()

    # Gira em quartos de volta e valida apenas a posição final, sem deslocamentos corretivos.
    def rotate(self, turns: int = 1) -> None:
        if (not self.running or self._paused_at is not None or self.active is None
                or self.active.kind == PieceKind.O):
            return
        p = self.active
        size = SHAPES[p.kind][0]
        cells = p.cells
        for _ in range(turns % 4):
            cells = tuple((size - 1 - y, x) for x, y in cells)
        candidate = Piece(p.kind, p.x, p.y, cells)
        if self._valid(candidate):
            self.active = candidate
            self._touch_ground()

    # Tenta descer uma linha e inicia a espera quando a peça apoia.
    def soft_drop(self) -> list[EngineEvent]:
        if not self.running or self._paused_at is not None or self.active is None:
            return []
        p = self.active
        candidate = Piece(p.kind, p.x, p.y + 1, p.cells)
        if self._valid(candidate):
            self.active = candidate
        self._touch_ground()
        return []

    # Desce até a última posição válida e fixa a peça imediatamente.
    def hard_drop(self) -> list[EngineEvent]:
        if not self.running or self._paused_at is not None or self.active is None:
            return []
        while True:
            p = self.active
            candidate = Piece(p.kind, p.x, p.y + 1, p.cells)
            if not self._valid(candidate):
                return self._lock()
            self.active = candidate

    # Atualiza a gravidade e fixa peças cujo prazo de apoio terminou.
    def tick(self) -> list[EngineEvent]:
        if not self.running or self._paused_at is not None:
            return []
        now = self.clock()
        self._touch_ground()
        if (self._lock_deadline is not None and now + 1e-9 >= self._lock_deadline
                and self._grounded()):
            return self._lock()
        steps = int((now - self._last_tick + 1e-9) / GRAVITY_SECONDS)
        events: list[EngineEvent] = []
        for _ in range(min(steps, MAX_CATCH_UP_STEPS)):
            self._last_tick += GRAVITY_SECONDS
            events.extend(self.soft_drop())
            if not self.running:
                break
        # Descarta o atraso acumulado excedente para manter a entrada e o desenho responsivos.
        if steps > MAX_CATCH_UP_STEPS:
            self._last_tick = now
        return events

    # Fixa, limpa linhas, aplica lixo e produz ataque, tabuleiro e derrota.
    def _lock(self) -> list[EngineEvent]:
        assert self.active is not None
        pending_before = min(self.pending_garbage, MAX_GARBAGE_PER_LOCK)
        for x, y in self.active.occupied():
            self.board[y][x] = int(self.active.kind)
        self.active = None
        survivors = [row for row in self.board if not all(row)]
        cleared = HEIGHT - len(survivors)
        self.board = [[0] * WIDTH for _ in range(cleared)] + survivors
        self.score += SCORE_BY_LINES[cleared]
        events: list[EngineEvent] = []
        attack = ATTACK_BY_LINES[cleared]
        if attack:
            events.append(AttackProduced(attack))
        overflow = False
        for _ in range(pending_before):
            overflow |= any(self.board.pop(0))
            hole = self.garbage_rng.randrange(WIDTH)
            self.board.append([0 if x == hole else 8 for x in range(WIDTH)])
        self.pending_garbage -= pending_before
        if overflow:
            self.loss = LossReason.OVERFLOW
            self.running = False
        else:
            self.hold_used = False
            self._spawn()
        events.append(BoardProduced(self.snapshot()))
        if self.loss is not None:
            events.append(LocalDefeat(self.loss))
        self._last_tick = self.clock()
        return events
