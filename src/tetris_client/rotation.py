"""Rotação por matriz e deslocamentos corretivos próprios deste jogo."""

from tetris_shared.models import PieceKind

# Preserva os encaixes antigos antes de tentar as correções mais agressivas.
# y negativo sobe. Estas tabelas são próprias do projeto.
KICKS = {
    1: ((0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0), (0, -2)),
    2: ((0, 0), (0, -1), (-1, 0), (1, 0), (0, -2), (-2, 0), (2, 0)),
    3: ((0, 0), (1, 0), (-1, 0), (0, -1), (2, 0), (-2, 0), (0, -2)),
}


SQUEEZE_KICKS = (
    (0, 1), (-1, 1), (1, 1), (-1, -1), (1, -1),
    (0, 2), (-1, 2), (1, 2), (-1, -2), (1, -2),
    (-2, -1), (2, -1), (-2, 1), (2, 1),
    (-2, -2), (2, -2), (-2, 2), (2, 2),
)
I_REACH_KICKS = ((-3, 0), (3, 0), (-3, -1), (3, -1), (-3, 1), (3, 1))


def kick_offsets(kind: PieceKind, turns: int) -> tuple[tuple[int, int], ...]:
    """Acrescenta encaixes sob saliências, espelhando a preferência no anti-horário."""
    turns %= 4
    if kind == PieceKind.O or turns == 0:
        return ((0, 0),)
    extra = SQUEEZE_KICKS
    if kind == PieceKind.I:
        # A barra longa pode alcançar uma cavidade até três colunas ao lado.
        extra += I_REACH_KICKS
    if turns == 3:
        extra = tuple((-dx, dy) for dx, dy in extra)
    return KICKS[turns] + extra


def rotated_cells(cells: tuple[tuple[int, int], ...], size: int,
                  turns: int) -> tuple[tuple[int, int], ...]:
    """Calcula a orientação final, inclusive 180°, sem posições intermediárias."""
    for _ in range(turns % 4):
        cells = tuple((size - 1 - y, x) for x, y in cells)
    return cells
