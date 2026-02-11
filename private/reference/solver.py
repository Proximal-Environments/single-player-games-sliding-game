"""Sliding puzzle solver — fully constructive, fully deterministic.

Row-by-row, column-by-column placement strategy with zero search:
  - Blank routing: deterministic L-shaped paths (2–4 straight segments).
    Tries H→V, V→H, then multi-phase interior/boundary detours, then
    a 1-step escape + L-path.  No BFS, no DFS, no visit tracking.
  - Individual tiles: constructive step-by-step push.
  - Last two per strip: bottom-corner-first parking of the second
    tile, then staging + rotation with notch freeze.
  - Final 2×2: at most two clockwise rotations.
"""

from __future__ import annotations

from backend.models.board import Board, Direction


# ======================================================================
#  Board wrapper — flat representation with precomputed adjacency
# ======================================================================

class _B:
    __slots__ = ("n", "nn", "g", "p", "bi", "adj", "_dm")

    def __init__(self, board: Board) -> None:
        n = board.size
        nn = n * n
        self.n = n
        self.nn = nn

        g = [0] * nn
        p = [0] * nn
        for r in range(n):
            base = r * n
            for c in range(n):
                v = board.tiles[r][c]
                g[base + c] = v
                p[v] = base + c
        self.g = g
        self.p = p
        self.bi = board.blank_pos[0] * n + board.blank_pos[1]

        adj: list[tuple[int, ...]] = [() for _ in range(nn)]
        for i in range(nn):
            r, c = divmod(i, n)
            nb: list[int] = []
            if r > 0:     nb.append(i - n)
            if r < n - 1: nb.append(i + n)
            if c > 0:     nb.append(i - 1)
            if c < n - 1: nb.append(i + 1)
            adj[i] = tuple(nb)
        self.adj = adj
        self._dm = {
            n: Direction.UP, -n: Direction.DOWN,
            1: Direction.LEFT, -1: Direction.RIGHT,
        }

    def sw(self, ni: int, out: list[Direction]) -> None:
        out.append(self._dm[ni - self.bi])
        bi = self.bi
        g = self.g
        p = self.p
        tv = g[ni]
        g[bi] = tv
        g[ni] = 0
        p[tv] = bi
        p[0] = ni
        self.bi = ni

    def snap(self) -> tuple[list[int], list[int], int]:
        return self.g[:], self.p[:], self.bi

    def restore(self, s: tuple[list[int], list[int], int]) -> None:
        self.g[:] = s[0]
        self.p[:] = s[1]
        self.bi = s[2]


# ======================================================================
#  Blank routing — deterministic L-path + step escape
# ======================================================================

def _lpath(bi: int, tgt: int, n: int, fz: bytearray,
           h_first: bool) -> list[int] | None:
    """Try to build a clear L-shaped path (two straight segments).

    Returns the list of cells to traverse, or ``None`` if any cell
    along the path is frozen.
    """
    br = bi // n;  bc = bi - br * n
    tr = tgt // n; tc = tgt - tr * n
    path: list[int] = []
    r, c = br, bc

    if h_first:
        dc = (c < tc) - (c > tc)
        while c != tc:
            c += dc; cell = r * n + c
            if fz[cell]: return None
            path.append(cell)
        dr = (r < tr) - (r > tr)
        while r != tr:
            r += dr; cell = r * n + c
            if fz[cell]: return None
            path.append(cell)
    else:
        dr = (r < tr) - (r > tr)
        while r != tr:
            r += dr; cell = r * n + c
            if fz[cell]: return None
            path.append(cell)
        dc = (c < tc) - (c > tc)
        while c != tc:
            c += dc; cell = r * n + c
            if fz[cell]: return None
            path.append(cell)
    return path


def _lpath3(bi: int, tgt: int, n: int, fz: bytearray) -> list[int] | None:
    """3-phase path: go perpendicular, straight, perpendicular back.

    Handles the collinear case (blank and target share a row/column
    with a frozen cell between them) by detouring through an adjacent
    row or column.  Tries all four perpendicular directions (DOWN,
    RIGHT, UP, LEFT) with increasing offsets.
    """
    br = bi // n;  bc = bi - br * n
    tr = tgt // n; tc = tgt - tr * n

    # go-low: DOWN → H → UP
    for sr in range(max(br, tr) + 1, n):
        path: list[int] = []; r = br; c = bc; ok = True
        while r < sr:
            r += 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        dc = (c < tc) - (c > tc)
        while ok and c != tc:
            c += dc; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        while ok and r > tr:
            r -= 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if ok: return path

    # go-right: RIGHT → V → LEFT
    for sc in range(max(bc, tc) + 1, n):
        path = []; r = br; c = bc; ok = True
        while c < sc:
            c += 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        dr = (r < tr) - (r > tr)
        while ok and r != tr:
            r += dr; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        while ok and c > tc:
            c -= 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if ok: return path

    # go-high: UP → H → DOWN
    for sr in range(min(br, tr) - 1, -1, -1):
        path = []; r = br; c = bc; ok = True
        while r > sr:
            r -= 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        dc = (c < tc) - (c > tc)
        while ok and c != tc:
            c += dc; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        while ok and r < tr:
            r += 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if ok: return path

    # go-left: LEFT → V → RIGHT
    for sc in range(min(bc, tc) - 1, -1, -1):
        path = []; r = br; c = bc; ok = True
        while c > sc:
            c -= 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        dr = (r < tr) - (r > tr)
        while ok and r != tr:
            r += dr; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if not ok: continue
        while ok and c < tc:
            c += 1; cell = r * n + c
            if fz[cell]: ok = False; break
            path.append(cell)
        if ok: return path

    return None


def _bto(b: _B, o: list[Direction], tgt: int, fz: bytearray) -> None:
    """Move the blank to *tgt*, avoiding frozen cells.

    Purely deterministic — no search, no walk, no visit tracking.

    1. **L-path** (H→V or V→H) — covers the majority of remaining
       calls (after the _mto around-maneuver handles collinear cases).
    2. **3-phase path** — for the collinear / 2-obstacle case.
    3. **1-step escape** — try each neighbour fully.
    4. **2-step escape** — for very tight staging.
    """
    if b.bi == tgt:
        return
    n = b.n
    bi = b.bi
    sw = b.sw

    # ---- L-path (H→V then V→H) ----
    path = _lpath(bi, tgt, n, fz, True)
    if path is None:
        path = _lpath(bi, tgt, n, fz, False)
    if path is not None:
        for cell in path:
            sw(cell, o)
        return

    # ---- 3-phase path ----
    path = _lpath3(bi, tgt, n, fz)
    if path is not None:
        for cell in path:
            sw(cell, o)
        return

    # ---- 1-step escape: try each neighbour fully ----
    adj = b.adj
    for ne in adj[bi]:
        if fz[ne]:
            continue
        p = _lpath(ne, tgt, n, fz, True)
        if p is None:
            p = _lpath(ne, tgt, n, fz, False)
        if p is None:
            p = _lpath3(ne, tgt, n, fz)
        if p is not None:
            sw(ne, o)
            for cell in p:
                sw(cell, o)
            return

    # ---- 2-step escape (very rare) ----
    for ne in adj[bi]:
        if fz[ne]:
            continue
        for ne2 in adj[ne]:
            if fz[ne2] or ne2 == bi:
                continue
            p = _lpath(ne2, tgt, n, fz, True)
            if p is None:
                p = _lpath(ne2, tgt, n, fz, False)
            if p is None:
                p = _lpath3(ne2, tgt, n, fz)
            if p is not None:
                sw(ne, o)
                sw(ne2, o)
                for cell in p:
                    sw(cell, o)
                return

    raise RuntimeError(f"_bto: no path bi={bi} tgt={tgt}")


# ======================================================================
#  Single-tile mover — constructive step-by-step
# ======================================================================

def _mto(b: _B, o: list[Direction], v: int,
         gi: int, fz: bytearray) -> None:
    n = b.n
    nn = n * n
    adj = b.adj
    sw = b.sw
    max_steps = 4 * nn

    for _ in range(max_steps):
        ti = b.p[v]
        if ti == gi:
            return

        tr = ti // n
        tc = ti - tr * n
        gr = gi // n
        gc = gi - gr * n

        # Pick direction: column-first, row-second, detour if blocked.
        delta = 0

        if tc != gc:
            d = 1 if tc < gc else -1
            if not fz[ti + d]:
                delta = d

        if delta == 0 and tr != gr:
            d = n if tr < gr else -n
            if not fz[ti + d]:
                delta = d

        if delta == 0:
            for ne in adj[ti]:
                if not fz[ne]:
                    delta = ne - ti
                    break

        if delta == 0:
            raise RuntimeError(f"_mto stuck: v={v} ti={ti} gi={gi}")

        target = ti + delta
        fz[ti] = 1

        # --- Fast path: blank is right behind tile → 4-step around ---
        bi = b.bi
        if bi == ti - delta:
            done = False
            if delta == 1 or delta == -1:        # horizontal push
                if bi // n == ti // n:          # same row (no wrapping)
                    for perp in (n, -n):
                        c1 = bi + perp
                        if c1 < 0 or c1 >= nn:
                            continue
                        c3 = target + perp
                        if c3 < 0 or c3 >= nn:
                            continue
                        c2 = ti + perp
                        if fz[c1] or fz[c2] or fz[c3]:
                            continue
                        sw(c1, o); sw(c2, o); sw(c3, o)
                        sw(target, o)
                        done = True; break
            else:                               # vertical push
                if bi % n == ti % n:            # same col (no wrapping)
                    for perp in (1, -1):
                        c1 = bi + perp
                        if c1 < 0 or c1 >= nn:
                            continue
                        if c1 // n != bi // n:  # column wrap guard
                            continue
                        c3 = target + perp
                        if c3 < 0 or c3 >= nn:
                            continue
                        c2 = ti + perp
                        if fz[c1] or fz[c2] or fz[c3]:
                            continue
                        sw(c1, o); sw(c2, o); sw(c3, o)
                        sw(target, o)
                        done = True; break
            if done:
                fz[ti] = 0; sw(ti, o); continue
        # --- Full _bto routing ---
        _bto(b, o, target, fz)
        fz[ti] = 0
        sw(ti, o)

    raise RuntimeError(f"_mto max iterations: v={v} gi={gi}")


# ======================================================================
#  Last-two placement — bottom-corner-first strategy
#
#  Park vb far from the staging area (bottom of the last column for
#  rows, rightmost of the last row for columns) so that va staging
#  needs no extra frozen cells.  Once va is locked in, the notch
#  freeze is the only extra constraint for vb staging.
# ======================================================================

def _last2_row(b: _B, o: list[Direction], r: int, last: int,
               va: int, vb: int, fz: bytearray) -> None:
    """Place the last two tiles of row *r*.

    Strategy (user-suggested "bottom-corner-first"):
      1. Park vb at the bottom of the last column — far from the
         staging area so it won't be displaced into the notch.
      2. Stage va at the corner ``(r, last)`` — no vb freeze needed.
      3. Stage vb below the corner ``(r+1, last)`` with the notch
         frozen (standard safeguard).
      4. 3-swap clockwise rotation to place both tiles.
    """
    n = b.n
    gi_a  = r * n + last - 1
    gi_b  = r * n + last
    if b.p[va] == gi_a and b.p[vb] == gi_b:
        return

    stg_a  = r * n + last             # va staging  (corner)
    stg_b  = (r + 1) * n + last       # vb staging  (below corner)
    bl_stg = (r + 1) * n + last - 1   # blank for rotation
    notch  = r * n + last - 1         # dead-end when stg_a frozen

    for _attempt in range(4):
        snap    = b.snap()
        fz_snap = bytes(fz)
        trial: list[Direction] = []

        try:
            # --- park vb at the bottom of the last column -----------------
            park = (n - 1) * n + last
            if b.p[vb] != stg_b and b.p[vb] != park:
                _mto(b, trial, vb, park, fz)

            # --- stage va at the corner -----------------------------------
            _mto(b, trial, va, stg_a, fz)
            fz[stg_a] = 1

            # Safety: if vb drifted into the notch, retry.
            if b.p[vb] == notch:
                raise RuntimeError("vb in notch after staging va")

            # --- stage vb below the corner --------------------------------
            fz[notch] = 1
            _mto(b, trial, vb, stg_b, fz)
            fz[notch] = 0

            fz[stg_b] = 1
            _bto(b, trial, bl_stg, fz)

            # 3-swap clockwise rotation
            b.sw(notch, trial)
            b.sw(stg_a, trial)
            b.sw(stg_b, trial)

            fz[:] = fz_snap
            if b.p[va] == gi_a and b.p[vb] == gi_b:
                o.extend(trial)
                return

            b.restore(snap)
        except (RuntimeError, KeyError):
            b.restore(snap)
            fz[:] = fz_snap

        # Push vb further away before retrying.
        safe_r = min(n - 1, r + 2 + _attempt)
        safe_c = min(last - _attempt % 2, n - 1)
        _mto(b, o, vb, safe_r * n + safe_c, fz)

    raise RuntimeError(f"_last2_row: exhausted retries r={r} last={last}")


def _last2_col(b: _B, o: list[Direction], c: int, last: int,
               va: int, vb: int, fz: bytearray) -> None:
    """Place the last two tiles of column *c*.

    Mirror of ``_last2_row`` — parks vb at the rightmost position of
    the last row, then stages va at the bottom of the column, vb to
    its right, and performs a 3-swap rotation.
    """
    n = b.n
    gi_a  = (last - 1) * n + c
    gi_b  = last * n + c
    if b.p[va] == gi_a and b.p[vb] == gi_b:
        return

    stg_a  = last * n + c             # va staging  (bottom of col)
    stg_b  = last * n + c + 1         # vb staging  (right of bottom)
    bl_stg = (last - 1) * n + c + 1   # blank for rotation
    notch  = (last - 1) * n + c       # dead-end when stg_a frozen

    for _attempt in range(4):
        snap    = b.snap()
        fz_snap = bytes(fz)
        trial: list[Direction] = []

        try:
            # --- park vb at the rightmost position of the last row --------
            park = last * n + (n - 1)
            if b.p[vb] != stg_b and b.p[vb] != park:
                _mto(b, trial, vb, park, fz)

            # --- stage va at the bottom of the column ---------------------
            _mto(b, trial, va, stg_a, fz)
            fz[stg_a] = 1

            if b.p[vb] == notch:
                raise RuntimeError("vb in notch after staging va")

            # --- stage vb to the right of the bottom ----------------------
            fz[notch] = 1
            _mto(b, trial, vb, stg_b, fz)
            fz[notch] = 0

            fz[stg_b] = 1
            _bto(b, trial, bl_stg, fz)

            b.sw(notch, trial)
            b.sw(stg_a, trial)
            b.sw(stg_b, trial)

            fz[:] = fz_snap
            if b.p[va] == gi_a and b.p[vb] == gi_b:
                o.extend(trial)
                return

            b.restore(snap)
        except (RuntimeError, KeyError):
            b.restore(snap)
            fz[:] = fz_snap

        # Push vb further away before retrying.
        safe_r = last
        safe_c = min(n - 1, c + 2 + _attempt)
        _mto(b, o, vb, safe_r * n + safe_c, fz)

    raise RuntimeError(f"_last2_col: exhausted retries c={c} last={last}")


# ======================================================================
#  Row / column strip solvers
# ======================================================================

def _row(b: _B, o: list[Direction], off: int, fz: bytearray) -> None:
    n = b.n
    r = off
    last = n - 1
    base = r * n
    for c in range(off, last - 1):
        _mto(b, o, base + c + 1, base + c, fz)
        fz[base + c] = 1
    va = base + last
    vb = base + last + 1
    _last2_row(b, o, r, last, va, vb, fz)
    fz[base + last - 1] = 1
    fz[base + last] = 1


def _col(b: _B, o: list[Direction], off: int, fz: bytearray) -> None:
    n = b.n
    c = off
    last = n - 1
    for r in range(off + 1, last - 1):
        _mto(b, o, r * n + c + 1, r * n + c, fz)
        fz[r * n + c] = 1
    va = (last - 1) * n + c + 1
    vb = last * n + c + 1
    _last2_col(b, o, c, last, va, vb, fz)
    fz[(last - 1) * n + c] = 1
    fz[last * n + c] = 1


# ======================================================================
#  2×2 endgame — at most two clockwise rotations
# ======================================================================

def _solve_2x2(b: _B, o: list[Direction], off: int,
               fz: bytearray) -> None:
    n = b.n
    tl = off * n + off
    tr = tl + 1
    bl = tl + n
    br = bl + 1

    g_tl = tl + 1
    g_tr = tr + 1
    g_bl = bl + 1

    if b.g[tl] == g_tl and b.g[tr] == g_tr and b.g[bl] == g_bl:
        return

    _bto(b, o, br, fz)

    for _ in range(2):
        if b.g[tl] == g_tl and b.g[tr] == g_tr and b.g[bl] == g_bl:
            return
        b.sw(bl, o)
        b.sw(tl, o)
        b.sw(tr, o)
        b.sw(br, o)


# ======================================================================
#  Full solve
# ======================================================================

def _solve(b: _B, o: list[Direction]) -> None:
    n = b.n
    fz = bytearray(b.nn)
    off = 0
    while n - off > 2:
        _row(b, o, off, fz)
        _col(b, o, off, fz)
        off += 1
    if n - off == 2:
        _solve_2x2(b, o, off, fz)


# ======================================================================
#  Public API
# ======================================================================

class Solver:
    @staticmethod
    def solve(board: Board) -> list[Direction]:
        """Return a move sequence that solves *board*, or ``[]`` if unsolvable."""
        if board.is_solved():
            return []
        if not Solver.is_solvable(board):
            return []
        wb = _B(board)
        moves: list[Direction] = []
        _solve(wb, moves)
        return moves

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
