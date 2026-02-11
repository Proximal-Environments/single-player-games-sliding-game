"""Core gameplay logic — processes moves and checks win condition."""

from __future__ import annotations

from backend.engine.gamegenerator import GameGenerator
from backend.engine.gamestate import GameState
from backend.models.board import Board, Direction


class GamePlay:
    """Orchestrates a single game session."""

    def __init__(self, size: int) -> None:
        self.size = size
        board = GameGenerator.generate(size)
        self.state = GameState(board)

    @classmethod
    def from_board(cls, board: Board) -> "GamePlay":
        """Create a game session from an existing board (e.g. loaded from file)."""
        obj = object.__new__(cls)
        obj.size = board.size
        obj.state = GameState(board)
        return obj

    # -- movement (direction = where the *tile* moves) ------------------------

    def move(self, direction: Direction) -> bool:
        """Slide a tile in *direction* into the adjacent blank.

        E.g. ``Direction.UP`` moves the tile **below** the blank upward.
        Returns True if the move was valid.
        """
        board = self.state.board
        br, bc = board.blank_pos

        # The offset points to the tile that will slide into the blank.
        # UP   → tile at (br+1, bc) moves up   → blank shifts down
        # DOWN → tile at (br-1, bc) moves down  → blank shifts up
        # LEFT → tile at (br, bc+1) moves left  → blank shifts right
        # RIGHT→ tile at (br, bc-1) moves right → blank shifts left
        offsets = {
            Direction.UP: (1, 0),
            Direction.DOWN: (-1, 0),
            Direction.LEFT: (0, 1),
            Direction.RIGHT: (0, -1),
        }
        dr, dc = offsets[direction]
        tr, tc = br + dr, bc + dc

        if not (0 <= tr < board.size and 0 <= tc < board.size):
            return False

        self._swap(board, (tr, tc))
        self.state.increment_moves()
        return True

    def move_tile(self, row: int, col: int) -> bool:
        """Move a tile at (row, col) into the adjacent blank.

        Returns True if the tile was adjacent to the blank and the move
        was applied.
        """
        board = self.state.board
        br, bc = board.blank_pos

        if abs(row - br) + abs(col - bc) != 1:
            return False

        self._swap(board, (row, col))
        self.state.increment_moves()
        return True

    # -- queries --------------------------------------------------------------

    @property
    def is_won(self) -> bool:
        return self.state.is_solved

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _swap(board: Board, target: tuple[int, int]) -> None:
        br, bc = board.blank_pos
        tr, tc = target
        board.tiles[br][bc], board.tiles[tr][tc] = (
            board.tiles[tr][tc],
            board.tiles[br][bc],
        )
        board.blank_pos = (tr, tc)
