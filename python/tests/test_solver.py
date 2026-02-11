"""Solver test suite — parametric benchmarks.

Boards are pre-generated JSON fixtures under ``<project_root>/fixtures/``.
Every test is hard-killed after 1 s by ``pytest-timeout`` (configured in
``pyproject.toml``).  If the solver returns in time, the move list is
replayed through the real game engine to verify correctness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.engine.gameplay.game import GamePlay
from backend.engine.gamesolver.solver import Solver
from backend.models.board import Board, Direction

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


# -- fixture loaders ----------------------------------------------------------


def _load(name: str) -> list[dict]:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def _ids(board_data: dict) -> str:
    return board_data["id"]


# Loaded once at import time; each entry becomes one parametrised case.
_BOARDS_3x3 = _load("3x3.json")
_BOARDS_7x7 = _load("7x7.json")
_BOARDS_10x10 = _load("10x10.json")
_BOARDS_12x12 = _load("12x12.json")


# -- helpers ------------------------------------------------------------------


def _board_from_data(data: dict) -> Board:
    """Reconstruct a ``Board`` from its JSON representation."""
    size = data["size"]
    tiles = [row[:] for row in data["tiles"]]
    blank_pos: tuple[int, int] = (0, 0)
    for r, row in enumerate(tiles):
        for c, v in enumerate(row):
            if v == 0:
                blank_pos = (r, c)
    return Board(size=size, tiles=tiles, blank_pos=blank_pos)


def _assert_solve(data: dict) -> None:
    """Solve the board and verify the returned moves reach the goal state."""
    board = _board_from_data(data)

    moves = Solver.solve(board)

    # ---- move-list sanity ---------------------------------------------------
    assert isinstance(moves, list), "solve() must return a list of Direction"
    assert len(moves) > 0, f"Solvable board returned 0 moves ({data['id']})"
    assert all(isinstance(m, Direction) for m in moves), (
        "Every element must be a Direction"
    )

    # ---- apply moves via the real game engine and check win -----------------
    game = GamePlay.from_board(board)
    for i, direction in enumerate(moves):
        ok = game.move(direction)
        assert ok, (
            f"Move {i} ({direction.value}) was invalid at blank "
            f"{game.state.board.blank_pos}  ({data['id']})"
        )

    assert game.is_won, (
        f"Board not solved after {len(moves)} moves ({data['id']})"
    )


# -- tests --------------------------------------------------------------------


@pytest.mark.parametrize("board_data", _BOARDS_3x3, ids=_ids)
def test_solve_3x3(board_data: dict) -> None:
    _assert_solve(board_data)


@pytest.mark.parametrize("board_data", _BOARDS_7x7, ids=_ids)
def test_solve_7x7(board_data: dict) -> None:
    _assert_solve(board_data)


@pytest.mark.parametrize("board_data", _BOARDS_10x10, ids=_ids)
def test_solve_10x10(board_data: dict) -> None:
    _assert_solve(board_data)


@pytest.mark.parametrize("board_data", _BOARDS_12x12, ids=_ids)
def test_solve_12x12(board_data: dict) -> None:
    _assert_solve(board_data)
