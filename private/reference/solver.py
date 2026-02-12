"""Sliding puzzle solver — constructive approach, optimised hot path.

Strategy: solve row-by-row and column-by-column.
  - Place tiles left-to-right in each row; hook technique for the last two.
  - Place tiles top-to-bottom in each column; mirror hook for the last two.
  - Finish with a 2×2 endgame rotation.

Directions use tile-movement semantics (matching the game engine):
  Direction.UP   → tile below blank moves up   (blank shifts down)
  Direction.DOWN → tile above blank moves down  (blank shifts up)
  Direction.LEFT → tile right of blank moves left (blank shifts right)
  Direction.RIGHT→ tile left of blank moves right (blank shifts left)

Performance notes:
  - Flat 1-D grid (g) and position array (p) — single-index lookups.
  - Blank position tracked as a single int (bi = r*n+c).
  - Direction→delta dict replaces if/elif chain in mv().
  - Swap inlined in go/go_vf routing loops (eliminates call overhead).
"""

from __future__ import annotations

from backend.models.board import Board, Direction


class Solver:
    @staticmethod
    def solve(board: Board) -> list[Direction]:
        if board.is_solved():
            return []
        if not Solver.is_solvable(board):
            return []

        n = board.size
        nm1 = n - 1

        # ── flat data structures ────────────────────────────
        # g[r*n+c] = tile value;  p[tile_value] = flat index
        nn = n * n
        g = [0] * nn
        p = [0] * nn
        for r in range(n):
            base = r * n
            for c in range(n):
                v = board.tiles[r][c]
                g[base + c] = v
                p[v] = base + c
        bi = board.blank_pos[0] * n + board.blank_pos[1]

        out: list[Direction] = []
        _oa = out.append                       # cached method

        # ── cached direction constants ──────────────────────
        _U = Direction.UP;   _D = Direction.DOWN
        _L = Direction.LEFT; _R = Direction.RIGHT
        _dd = {_U: n, _D: -n, _L: 1, _R: -1}  # tile-dir → blank delta

        # ── move primitive ──────────────────────────────────

        def mv(d: Direction) -> None:
            nonlocal bi
            ni = bi + _dd[d]
            tv = g[ni]; g[bi] = tv; g[ni] = 0; p[tv] = bi; bi = ni
            _oa(d)

        # ── blank routing (swap inlined for speed) ──────────

        def go(dr: int, dc: int) -> None:
            """Route blank to (dr, dc): horizontal first, then vertical."""
            nonlocal bi
            bc = bi % n
            while bc > dc:
                ni = bi - 1; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_R); bc -= 1
            while bc < dc:
                ni = bi + 1; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_L); bc += 1
            br = bi // n
            while br > dr:
                ni = bi - n; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_D); br -= 1
            while br < dr:
                ni = bi + n; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_U); br += 1

        def go_vf(dr: int, dc: int) -> None:
            """Route blank to (dr, dc): vertical first, then horizontal."""
            nonlocal bi
            br = bi // n
            while br > dr:
                ni = bi - n; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_D); br -= 1
            while br < dr:
                ni = bi + n; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_U); br += 1
            bc = bi % n
            while bc > dc:
                ni = bi - 1; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_R); bc -= 1
            while bc < dc:
                ni = bi + 1; tv = g[ni]; g[bi] = tv; g[ni] = 0
                p[tv] = bi; bi = ni; _oa(_L); bc += 1

        # ── tile pushers ────────────────────────────────────

        def push_right(tile: int, dest_col: int) -> None:
            ti = p[tile]; ec = ti % n
            if ec >= dest_col:
                return
            er = ti // n
            br = bi // n; bc = bi % n

            if br == er and bc <= ec:
                mv(_U if br < nm1 else _D)
                go(er, ec + 1)
            elif br >= er:
                go(er, ec + 1)
            else:
                if bc == ec:
                    mv(_L if ec < nm1 else _R)
                if er < nm1:
                    go_vf(er + 1, ec + 1); mv(_D)
                else:
                    go_vf(er - 1, ec + 1); mv(_U)

            mv(_R)
            while True:
                ti = p[tile]; tc = ti % n
                if tc >= dest_col:
                    break
                if ti // n == nm1:
                    mv(_D); mv(_L); mv(_L); mv(_U); mv(_R)
                else:
                    mv(_U); mv(_L); mv(_L); mv(_D); mv(_R)

        def push_left(tile: int, dest_col: int) -> None:
            ti = p[tile]; ec = ti % n
            if ec <= dest_col:
                return
            er = ti // n
            br = bi // n; bc = bi % n

            if br == er and bc >= ec:
                mv(_U if br < nm1 else _D)
                go(er, ec - 1)
            elif br >= er:
                go(er, ec - 1)
            else:
                if bc == ec:
                    mv(_L if ec < nm1 else _R)
                if er < nm1:
                    go_vf(er + 1, ec - 1); mv(_D)
                else:
                    go_vf(er - 1, ec - 1); mv(_U)

            mv(_L)
            while True:
                ti = p[tile]; tc = ti % n
                if tc <= dest_col:
                    break
                if ti // n == nm1:
                    mv(_D); mv(_R); mv(_R); mv(_U); mv(_L)
                else:
                    mv(_U); mv(_R); mv(_R); mv(_D); mv(_L)

        def push_up(tile: int, dest_row: int) -> None:
            ti = p[tile]; er = ti // n
            if er <= dest_row:
                return
            ec = ti % n
            br = bi // n; bc = bi % n

            if er == nm1:
                # Tile at bottom row
                if bc == ec:
                    mv(_L if ec < nm1 else _R)
                if br == er:
                    mv(_D); go(er - 1, ec)
                elif br < er:
                    go_vf(er - 1, ec)
                else:
                    go(er - 1, ec)
                mv(_U)
            else:
                # Route blank below tile
                if bc == ec and br < er:
                    mv(_L if ec < nm1 else _R)
                if br <= er:
                    dc = ec + 1 if ec < nm1 else ec - 1
                    if br == er:
                        mv(_U); go(er + 1, dc)
                    else:
                        go_vf(er + 1, dc)
                    go(er + 1, ec)
                else:
                    go(er + 1, ec)
                if bi // n < p[tile] // n:
                    mv(_U)

            while True:
                ti = p[tile]; tr = ti // n
                if tr <= dest_row:
                    break
                if ti % n == nm1:
                    mv(_R); mv(_D); mv(_D); mv(_L); mv(_U)
                else:
                    mv(_L); mv(_D); mv(_D); mv(_R); mv(_U)

        def push_down(tile: int, dest_row: int) -> None:
            ti = p[tile]; er = ti // n
            if er >= dest_row:
                return
            ec = ti % n
            br = bi // n; bc = bi % n

            if bc == ec and br <= er:
                mv(_L if ec < nm1 else _R)
            if br <= er:
                dc = ec + 1 if ec < nm1 else ec - 1
                if br == er:
                    mv(_U); go(er + 1, dc)
                else:
                    go_vf(er + 1, dc)
                go(er + 1, ec)
            else:
                go(er + 1, ec)
            mv(_D)

            while True:
                ti = p[tile]; tr = ti // n
                if tr >= dest_row:
                    break
                if ti % n == nm1:
                    mv(_R); mv(_U); mv(_U); mv(_L); mv(_D)
                else:
                    mv(_L); mv(_U); mv(_U); mv(_R); mv(_D)

        def move_to(tile: int, dr: int, dc: int) -> None:
            tc = p[tile] % n
            if tc < dc:
                push_right(tile, dc)
            elif tc > dc:
                push_left(tile, dc)
            tr = p[tile] // n
            if tr > dr:
                push_up(tile, dr)
            elif tr < dr:
                push_down(tile, dr)

        def move_to_vf(tile: int, dr: int, dc: int) -> None:
            tr = p[tile] // n
            if tr > dr:
                push_up(tile, dr)
            elif tr < dr:
                push_down(tile, dr)
            tc = p[tile] % n
            if tc < dc:
                push_right(tile, dc)
            elif tc > dc:
                push_left(tile, dc)

        # ── row solver ──────────────────────────────────────

        def solve_row(row: int, col_start: int) -> None:
            base = row * n
            for c in range(col_start, nm1 - 1):
                move_to(base + c + 1, row, c)

            # Last two tiles: hook technique
            va = base + nm1          # → (row, nm1 - 1)
            vb = base + nm1 + 1      # → (row, nm1)
            if p[va] == base + nm1 - 1 and p[vb] == base + nm1:
                return

            # Escape: blank below committed row
            while bi // n <= row:
                mv(_U)

            move_to(vb, nm1, nm1)        # 1. park vb bottom-right
            move_to(va, row, nm1)         # 2. stage va at corner
            go(row + 1, nm1 - 1)          # 3. safe blank position
            move_to(vb, row + 1, nm1)     # 4. stage vb below corner
            go(row, nm1 - 1)              # 5. blank left of corner
            mv(_L)                        # va slides left
            mv(_U)                        # vb slides up

        # ── column solver ───────────────────────────────────

        def solve_col(col: int, row_start: int) -> None:
            for r in range(row_start, nm1 - 1):
                move_to_vf(r * n + col + 1, r, col)

            # Last two tiles: mirror hook
            va = (nm1 - 1) * n + col + 1  # → (nm1 - 1, col)
            vb = nm1 * n + col + 1         # → (nm1, col)
            if p[va] == (nm1 - 1) * n + col and p[vb] == nm1 * n + col:
                return

            # Escape: blank right of committed column
            while bi % n <= col:
                mv(_L)

            move_to_vf(vb, nm1, nm1)      # 1. park vb bottom-right
            move_to_vf(va, nm1, col)       # 2. stage va at bottom of col
            go_vf(nm1 - 1, col + 1)        # 3. safe blank position
            move_to_vf(vb, nm1, col + 1)   # 4. stage vb right of staging
            go_vf(nm1 - 1, col)            # 5. blank above staging
            mv(_U)                         # va slides up
            mv(_L)                         # vb slides left

        # ── 2×2 endgame ────────────────────────────────────

        def solve_2x2(off: int) -> None:
            tl = off * n + off
            g_tl = tl + 1
            g_tr = tl + 2
            g_bl = tl + n + 1

            go(off + 1, off + 1)

            for _ in range(3):
                if g[tl] == g_tl and g[tl + 1] == g_tr and g[tl + n] == g_bl:
                    return
                mv(_R); mv(_D); mv(_L); mv(_U)

        # ── orchestrate ─────────────────────────────────────

        off = 0
        while n - off > 2:
            solve_row(off, off)
            solve_col(off, off + 1)
            off += 1
        if n - off == 2:
            solve_2x2(off)

        return out

    @staticmethod
    def hint(board: Board) -> Direction | None:
        if board.is_solved():
            return None
        try:
            m = Solver.solve(board)
        except Exception:
            return None
        return m[0] if m else None

    @staticmethod
    def is_solvable(board: Board) -> bool:
        from bisect import bisect_left, insort
        n = board.size
        flat = [v for row in board.tiles for v in row if v != 0]
        inv = 0
        seen: list[int] = []
        for v in flat:
            inv += len(seen) - bisect_left(seen, v)
            insort(seen, v)
        if n % 2 == 1:
            return inv % 2 == 0
        blank_from_bottom = n - 1 - board.blank_pos[0]
        return (inv + blank_from_bottom) % 2 == 0
