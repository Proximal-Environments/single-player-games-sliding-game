#!/usr/bin/env python3
"""Generate pre-built test fixtures for the solver benchmark.

Run once from the ``python/`` directory::

    uv run python ../../private/scripts/generate_fixtures.py

    — or from the project root —

    cd python && uv run python ../private/scripts/generate_fixtures.py

Produces one JSON file per difficulty under ``<project_root>/fixtures/``.

**3×3 is exhaustive** — every one of the 181,440 solvable permutations
(9!/2) is included.  This gives a mathematical correctness guarantee:
if all 3×3 tests pass, the solver is correct for every possible 3×3
configuration.

Larger sizes use random sampling (500 boards each) plus handcrafted
edge cases (corner swaps).  Exhaustive testing is infeasible there
(7×7 has ~10^90 states), but because the algorithm uses the same
row-by-row / column-by-column code path for all sizes, correctness
on 3×3 + random sampling on larger sizes provides high confidence.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import sys
from pathlib import Path

# Resolve paths: this script lives in <project_root>/private/scripts/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PYTHON_ROOT = PROJECT_ROOT / "python"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from backend.engine.gamegenerator import GameGenerator  # noqa: E402
from backend.models.board import Board  # noqa: E402

FIXTURES_DIR = PROJECT_ROOT / "fixtures"
SEED = 42

# Random board counts for sizes where exhaustive testing is infeasible.
RANDOM_BOARD_COUNTS: dict[str, int] = {
    "7x7": 500,
    "10x10": 500,
    "12x12": 500,
}
DIFFICULTIES: dict[str, int] = {
    "3x3": 3,
    "7x7": 7,
    "10x10": 10,
    "12x12": 12,
}


# -- solvability (self-contained, no dependency on Solver) --------------------


def _is_solvable(board: Board) -> bool:
    n = board.size
    flat = [v for row in board.tiles for v in row if v != 0]
    inversions = 0
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            if flat[i] > flat[j]:
                inversions += 1
    if n % 2 == 1:
        return inversions % 2 == 0
    blank_row_from_bottom = n - 1 - board.blank_pos[0]
    return (inversions + blank_row_from_bottom) % 2 == 0


# -- hashing / uniqueness ----------------------------------------------------


def _board_hash(board: Board) -> str:
    """SHA-256 of the flattened tile list — deterministic, order-sensitive."""
    flat = tuple(v for row in board.tiles for v in row)
    return hashlib.sha256(str(flat).encode()).hexdigest()


# -- serialisation ------------------------------------------------------------


def _board_to_dict(board: Board, board_id: str) -> dict:
    return {
        "id": board_id,
        "size": board.size,
        "tiles": [row[:] for row in board.tiles],
    }


# -- exhaustive 3×3 generation ------------------------------------------------


def _generate_all_3x3() -> list[Board]:
    """Enumerate every solvable, non-trivial 3×3 permutation.

    9! = 362,880 total permutations.  Exactly half (181,440) are solvable.
    We exclude the already-solved identity (solver returns [] for it).
    Result: 181,439 boards.
    """
    n = 3
    solved = tuple(range(1, n * n)) + (0,)  # (1,2,3,4,5,6,7,8,0)
    boards: list[Board] = []
    for perm in itertools.permutations(range(n * n)):
        if perm == solved:
            continue  # skip identity — nothing to solve
        tiles = [list(perm[r * n : r * n + n]) for r in range(n)]
        bp = divmod(perm.index(0), n)
        board = Board(size=n, tiles=tiles, blank_pos=bp)
        if _is_solvable(board):
            boards.append(board)
    return boards


# -- random board generation --------------------------------------------------


def _generate_random_boards(
    size: int, count: int, seen: set[str]
) -> list[Board]:
    boards: list[Board] = []
    while len(boards) < count:
        board = GameGenerator.generate(size)
        assert _is_solvable(board), "Generated board failed solvability check"
        h = _board_hash(board)
        if h in seen:
            continue  # duplicate — regenerate
        seen.add(h)
        boards.append(board)
    return boards


# -- edge-case generation (corner swaps) --------------------------------------

_FIX_PAIRS: dict[str, str] = {
    "TL": "BR",
    "TR": "BL",
    "BL": "TR",
    "BR": "TL",
}


def _swap_positions(
    corner: str, direction: str, n: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    if corner == "TL":
        return ((0, 0), (0, 1)) if direction == "H" else ((0, 0), (1, 0))
    if corner == "TR":
        return ((0, n - 2), (0, n - 1)) if direction == "H" else ((0, n - 1), (1, n - 1))
    if corner == "BL":
        return ((n - 1, 0), (n - 1, 1)) if direction == "H" else ((n - 2, 0), (n - 1, 0))
    # BR — blank sits at (n-1, n-1), swap tiles 2-3 cells away
    return ((n - 1, n - 3), (n - 1, n - 2)) if direction == "H" else ((n - 3, n - 1), (n - 2, n - 1))


def _fix_swap_positions(
    opposite_corner: str, n: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    if opposite_corner == "TL":
        return (0, 0), (0, 1)
    if opposite_corner == "TR":
        return (0, n - 2), (0, n - 1)
    if opposite_corner == "BL":
        return (n - 1, 0), (n - 1, 1)
    return (n - 2, n - 2), (n - 2, n - 1)


def _apply_swap(board: Board, p1: tuple[int, int], p2: tuple[int, int]) -> None:
    r1, c1 = p1
    r2, c2 = p2
    board.tiles[r1][c1], board.tiles[r2][c2] = (
        board.tiles[r2][c2],
        board.tiles[r1][c1],
    )


def _generate_edge_cases_for_size(size: int, seen: set[str]) -> list[Board]:
    """Return corner-swap boards for one difficulty level."""
    n = size
    boards: list[Board] = []
    for corner in ("TL", "TR", "BL", "BR"):
        for direction in ("H", "V"):
            board = GameGenerator.solved(n)
            p1, p2 = _swap_positions(corner, direction, n)
            _apply_swap(board, p1, p2)

            if not _is_solvable(board):
                opp = _FIX_PAIRS[corner]
                fp1, fp2 = _fix_swap_positions(opp, n)
                if {fp1, fp2} & {p1, p2}:
                    mid = n // 2
                    fp1, fp2 = (mid, 0), (mid, 1)
                _apply_swap(board, fp1, fp2)
                assert _is_solvable(board), f"Parity fix failed: {size} {corner}_{direction}"

            assert not board.is_solved(), f"Edge case already solved: {size} {corner}_{direction}"

            h = _board_hash(board)
            if h not in seen:
                seen.add(h)
                boards.append(board)
            # If duplicate (extremely unlikely), silently skip — it means a
            # random board already had the same layout.
    return boards


# -- main ---------------------------------------------------------------------


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)

    # ---- 3×3: exhaustive (every solvable permutation) -----------------------
    print("Generating ALL solvable 3×3 permutations (9!/2 − 1) …")
    all_3x3 = _generate_all_3x3()
    random.shuffle(all_3x3)
    entries_3x3 = [
        _board_to_dict(b, f"board_3x3_{i:06d}")
        for i, b in enumerate(all_3x3)
    ]
    path_3x3 = FIXTURES_DIR / "3x3.json"
    with open(path_3x3, "w") as f:
        json.dump(entries_3x3, f, separators=(",", ":"))
    print(f"  → 3x3.json  ({len(entries_3x3)} boards — exhaustive) ✓")

    # ---- 7×7, 10×10, 12×12: random + edge cases ----------------------------
    for label, size in DIFFICULTIES.items():
        if label == "3x3":
            continue  # already handled above

        seen: set[str] = set()
        count = RANDOM_BOARD_COUNTS[label]

        # 1. Random boards
        print(f"Generating {count} random {label} boards …")
        random_boards = _generate_random_boards(size, count, seen)

        # 2. Edge-case boards (corner swaps)
        edge_boards = _generate_edge_cases_for_size(size, seen)
        print(f"  + {len(edge_boards)} edge-case boards")

        # 3. Merge & shuffle so edge cases are indistinguishable
        all_boards = random_boards + edge_boards
        random.shuffle(all_boards)

        # 4. Assign uniform sequential IDs
        entries = [
            _board_to_dict(b, f"board_{label}_{i:04d}")
            for i, b in enumerate(all_boards)
        ]

        # 5. Write
        path = FIXTURES_DIR / f"{label}.json"
        with open(path, "w") as f:
            json.dump(entries, f, separators=(",", ":"))

        total = len(entries)
        unique = len(seen)
        print(f"  → {path.name}  ({total} boards, {unique} unique hashes) ✓")

    print("Done!")


if __name__ == "__main__":
    main()
