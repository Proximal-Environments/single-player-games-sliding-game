"""Board model for the sliding puzzle game."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass
class Board:
    """Represents the sliding puzzle board.

    Tiles are stored as a 2D list of ints. 0 represents the blank space.
    """

    size: int
    tiles: list[list[int]]
    blank_pos: tuple[int, int]

    def get_tile(self, row: int, col: int) -> int:
        return self.tiles[row][col]

    def is_solved(self) -> bool:
        """Check if all tiles are in their goal positions."""
        expected = 1
        for r in range(self.size):
            for c in range(self.size):
                if r == self.size - 1 and c == self.size - 1:
                    return self.tiles[r][c] == 0
                if self.tiles[r][c] != expected:
                    return False
                expected += 1
        return True

    def is_tile_correct(self, row: int, col: int) -> bool:
        """Check if a specific tile is in its goal position."""
        val = self.tiles[row][col]
        if val == 0:
            return row == self.size - 1 and col == self.size - 1
        expected_row = (val - 1) // self.size
        expected_col = (val - 1) % self.size
        return row == expected_row and col == expected_col

    def copy(self) -> Board:
        return Board(
            size=self.size,
            tiles=[row[:] for row in self.tiles],
            blank_pos=self.blank_pos,
        )
