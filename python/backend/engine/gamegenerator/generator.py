"""Generates solvable sliding puzzle boards."""

from __future__ import annotations

import random

from backend.models.board import Board


class GameGenerator:
    """Creates solvable puzzles by shuffling from the solved state."""

    @staticmethod
    def generate(size: int) -> Board:
        """Return a random *solvable* board of the given size.

        The algorithm starts from the goal state and applies a large number
        of random valid moves, guaranteeing the result is always solvable.
        """
        # Build solved board
        tiles: list[list[int]] = []
        num = 1
        for r in range(size):
            row: list[int] = []
            for c in range(size):
                if r == size - 1 and c == size - 1:
                    row.append(0)
                else:
                    row.append(num)
                    num += 1
            tiles.append(row)

        board = Board(size=size, tiles=tiles, blank_pos=(size - 1, size - 1))

        # Shuffle by making random valid moves
        num_shuffles = size * size * 100
        prev_pos: tuple[int, int] | None = None

        for _ in range(num_shuffles):
            neighbors = GameGenerator._get_neighbors(board)
            # Avoid immediately undoing the previous move
            if prev_pos in neighbors and len(neighbors) > 1:
                neighbors.remove(prev_pos)
            target = random.choice(neighbors)
            prev_pos = board.blank_pos
            GameGenerator._swap(board, target)

        # Ensure the board is not already solved
        if board.is_solved():
            return GameGenerator.generate(size)

        return board

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _get_neighbors(board: Board) -> list[tuple[int, int]]:
        br, bc = board.blank_pos
        neighbors: list[tuple[int, int]] = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = br + dr, bc + dc
            if 0 <= nr < board.size and 0 <= nc < board.size:
                neighbors.append((nr, nc))
        return neighbors

    @staticmethod
    def _swap(board: Board, target: tuple[int, int]) -> None:
        br, bc = board.blank_pos
        tr, tc = target
        board.tiles[br][bc], board.tiles[tr][tc] = (
            board.tiles[tr][tc],
            board.tiles[br][bc],
        )
        board.blank_pos = (tr, tc)
