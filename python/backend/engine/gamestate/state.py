"""Tracks the mutable state of a game in progress."""

from __future__ import annotations

import time

from backend.models.board import Board


class GameState:
    """Holds the current board, move counter, and elapsed time."""

    def __init__(self, board: Board) -> None:
        self.board = board
        self.moves: int = 0
        self._start_time: float = time.time()
        self._elapsed_banked: float = 0.0
        self._running: bool = True

    # -- time tracking --------------------------------------------------------

    @property
    def elapsed_time(self) -> float:
        if self._running:
            return self._elapsed_banked + (time.time() - self._start_time)
        return self._elapsed_banked

    def pause(self) -> None:
        if self._running:
            self._elapsed_banked += time.time() - self._start_time
            self._running = False

    def resume(self) -> None:
        if not self._running:
            self._start_time = time.time()
            self._running = True

    # -- moves ----------------------------------------------------------------

    def increment_moves(self) -> None:
        self.moves += 1

    @property
    def is_solved(self) -> bool:
        return self.board.is_solved()
