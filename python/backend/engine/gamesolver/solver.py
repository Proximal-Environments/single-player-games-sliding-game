"""Sliding puzzle solver."""

from __future__ import annotations

from backend.models.board import Board, Direction


class Solver:
    """Stateless solver — all methods are static."""

    @staticmethod
    def solve(board: Board) -> list[Direction]:
        """Return a move sequence that solves *board*, or ``[]`` if unsolvable."""
        if board.is_solved():
            return []

        if not Solver.is_solvable(board):
            return []

        raise NotImplementedError("Solver.solve() is not yet implemented.")

    @staticmethod
    def hint(board: Board) -> Direction | None:
        """Return the single best next move, or ``None`` if solved / unsolvable."""
        if board.is_solved():
            return None

        try:
            moves = Solver.solve(board)
        except NotImplementedError:
            return None

        return moves[0] if moves else None

    @staticmethod
    def is_solvable(board: Board) -> bool:
        """Return True if *board* can reach the goal state."""
        raise NotImplementedError("Solver.is_solvable() is not yet implemented.")
