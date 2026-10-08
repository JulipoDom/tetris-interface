"""Avaliação pura de spins e limpezas; nenhuma mensagem ou E/S pertence aqui."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tetris_shared.models import PieceKind
from tetris_shared.rules import ATTACK_BY_LINES, HEIGHT, SCORE_BY_LINES, WIDTH

if TYPE_CHECKING:
    from .engine import Piece

T_SPIN_SCORE = (400, 800, 1200, 1600)
T_MINI_SCORE = (100, 200, 400)
T_SPIN_ATTACK = (0, 2, 4, 6)
T_MINI_ATTACK = (0, 0, 1)


@dataclass(frozen=True)
class ClearResult:
    """Resumo da última fixação, usado pelo motor e pelo painel local."""

    spin: str | None
    lines: int
    combo: int
    back_to_back: int
    score: int
    attack: int


def detect_spin(piece: "Piece", board: list[list[int]], rotated: bool) -> str | None:
    """Reconhece o encaixe antes de gravar a peça ou remover linhas completas."""
    if not rotated or piece.kind == PieceKind.O:
        return None

    def blocked(x: int, y: int) -> bool:
        """Trata bordas e blocos fixos como obstáculos para detectar o spin."""
        return not (0 <= x < WIDTH and 0 <= y < HEIGHT) or board[y][x] != 0

    if piece.kind == PieceKind.T:
        corners = ((0, 0), (2, 0), (0, 2), (2, 2))
        if sum(blocked(piece.x + x, piece.y + y) for x, y in corners) < 3:
            return None
        # As células já registram a orientação: a ponta fica oposta ao braço ausente.
        fronts = {
            (1, 2): ((0, 0), (2, 0)),
            (0, 1): ((2, 0), (2, 2)),
            (1, 0): ((0, 2), (2, 2)),
            (2, 1): ((0, 0), (0, 2)),
        }
        for missing_arm, front in fronts.items():
            if missing_arm not in piece.cells:
                full = all(blocked(piece.x + x, piece.y + y) for x, y in front)
                return "T-spin" if full else "T-spin mini"
        return None

    # As outras peças exigem imobilidade nas três direções de translação.
    if all(any(blocked(x + dx, y + dy) for x, y in piece.occupied())
           for dx, dy in ((-1, 0), (1, 0), (0, 1))):
        return f"{piece.kind.name}-spin"
    return None


def evaluate_clear(spin: str | None, lines: int, combo: int,
                   back_to_back: int) -> ClearResult:
    """Calcula score, combo e dano usando as regras de adaptação do projeto."""
    # Um T só pode fechar três linhas; mini triplo recebe a tabela completa.
    if spin == "T-spin mini" and lines == 3:
        spin = "T-spin"
    combo = combo + 1 if lines else -1
    difficult = lines > 0 and (lines == 4 or spin is not None)
    if lines:
        back_to_back = back_to_back + 1 if difficult else 0
    if spin == "T-spin":
        score, base = T_SPIN_SCORE[lines], T_SPIN_ATTACK[lines]
    elif spin == "T-spin mini":
        score, base = T_MINI_SCORE[lines], T_MINI_ATTACK[lines]
    else:
        score, base = SCORE_BY_LINES[lines], ATTACK_BY_LINES[lines]
    if not lines:
        return ClearResult(spin, lines, combo, back_to_back, score, 0)
    if difficult and back_to_back >= 2:
        base += 1
    # A divisão inteira mantém o arredondamento estável mesmo em combos longos.
    attack = base * (4 + combo) // 4
    if lines == 1 and base == 0:
        attack = (combo + 1).bit_length() - 1
    return ClearResult(spin, lines, combo, back_to_back, score + 50 * combo, attack)


def split_attack(amount: int) -> tuple[int, ...]:
    """Decompõe o total em quantidades aceitas pelo TVP/1 sem perder linhas."""
    attacks = []
    for quantity in (4, 2, 1):
        count, amount = divmod(amount, quantity)
        attacks.extend([quantity] * count)
    return tuple(attacks)
