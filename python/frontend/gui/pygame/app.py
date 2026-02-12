"""Pygame GUI frontend — fully self-contained.

Includes main menu, difficulty selection, gameplay, win screen,
and high-score display.  No terminal interaction required.
"""

from __future__ import annotations

import enum
import random
import time
from datetime import datetime
from pathlib import Path

import pygame

from backend.engine.gameplay import GamePlay
from backend.engine.gamesolver import Solver
from backend.models.board import Direction
from backend.models.highscore import HighScoreEntry, HighScoreManager

# ---------------------------------------------------------------------------
# Catppuccin Mocha palette
# ---------------------------------------------------------------------------
COL_BASE = (30, 30, 46)
COL_MANTLE = (24, 24, 37)
COL_SURFACE0 = (49, 50, 68)
COL_SURFACE1 = (69, 71, 90)
COL_OVERLAY0 = (108, 112, 134)
COL_TEXT = (205, 214, 244)
COL_SUBTEXT = (166, 173, 200)
COL_BLUE = (137, 180, 250)
COL_LAVENDER = (180, 190, 254)
COL_GREEN = (166, 227, 161)
COL_PINK = (245, 194, 231)
COL_YELLOW = (249, 226, 175)
COL_RED = (243, 139, 168)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
WIN_W, WIN_H = 500, 640
TILE_GAP = 4
MARGIN = 20
BOARD_MAX = WIN_W - 2 * MARGIN  # max board width/height in px


# ---------------------------------------------------------------------------
# Screen enum
# ---------------------------------------------------------------------------
class _Screen(enum.Enum):
    MENU = "menu"
    PLAYING = "playing"
    WIN = "win"
    SCORES = "scores"


# ---------------------------------------------------------------------------
# Simple clickable button
# ---------------------------------------------------------------------------
class _Btn:
    __slots__ = ("rect", "text", "font", "bg", "hover", "fg", "radius", "_hot")

    def __init__(
        self,
        rect: tuple[int, int, int, int],
        text: str,
        font: pygame.font.Font,
        *,
        bg: tuple = COL_SURFACE0,
        hover: tuple = COL_SURFACE1,
        fg: tuple = COL_TEXT,
        radius: int = 8,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.hover = hover
        self.fg = fg
        self.radius = radius
        self._hot = False

    def draw(self, surf: pygame.Surface) -> None:
        c = self.hover if self._hot else self.bg
        pygame.draw.rect(surf, c, self.rect, border_radius=self.radius)
        lbl = self.font.render(self.text, True, self.fg)
        surf.blit(
            lbl,
            (
                self.rect.centerx - lbl.get_width() // 2,
                self.rect.centery - lbl.get_height() // 2,
            ),
        )

    def motion(self, pos: tuple[int, int]) -> None:
        self._hot = self.rect.collidepoint(pos)

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


# ---------------------------------------------------------------------------
# Centring helpers
# ---------------------------------------------------------------------------
def _cx(w: int) -> int:
    return (WIN_W - w) // 2


def _blit_center(surf: pygame.Surface, rendered: pygame.Surface, y: int) -> None:
    surf.blit(rendered, (_cx(rendered.get_width()), y))


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class PygameApp:
    def __init__(self, default_size: int, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._hs = HighScoreManager(data_dir / "highscores.json")
        self._sel_size = default_size if default_size in (3, 7, 10, 12) else 3
        self._images_dir = data_dir.parent / "assets" / "images"
        self._tile_images: dict[int, pygame.Surface] = {}
        self._ref_image: pygame.Surface | None = None

        pygame.init()
        self._surf = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Sliding Puzzle")
        self._clock = pygame.time.Clock()

        # Fonts
        self._f_big = pygame.font.SysFont("Helvetica", 38, bold=True)
        self._f_title = pygame.font.SysFont("Helvetica", 22, bold=True)
        self._f_body = pygame.font.SysFont("Helvetica", 16)
        self._f_btn = pygame.font.SysFont("Helvetica", 17, bold=True)
        self._f_btn_sm = pygame.font.SysFont("Helvetica", 14, bold=True)
        self._f_small = pygame.font.SysFont("Helvetica", 13)
        self._f_score = pygame.font.SysFont("Helvetica", 14)

        self._screen = _Screen.MENU
        self._game: GamePlay | None = None
        self._won = False
        self._study_mode = False
        self._status_msg: str = ""

        # Pre-build buttons that don't move
        self._build_menu_btns()
        self._build_score_btns()
        self._build_game_btns()

    # ── menu buttons ────────────────────────────────────────────────────────

    _DIFFICULTIES: list[tuple[str, int]] = [
        ("Easy 3\u00d73", 3),
        ("Medium 7\u00d77", 7),
        ("Hard 10\u00d710", 10),
        ("V.Hard 12\u00d712", 12),
    ]

    def _build_menu_btns(self) -> None:
        bw, bh = 112, 46
        diffs = self._DIFFICULTIES
        gap = 8
        total_w = len(diffs) * bw + (len(diffs) - 1) * gap
        sx = _cx(total_w)

        self._size_btns: dict[int, _Btn] = {}
        for i, (label, s) in enumerate(diffs):
            x = sx + i * (bw + gap)
            self._size_btns[s] = _Btn(
                (x, 250, bw, bh),
                label,
                self._f_btn_sm,
            )

        bw_lg = 220
        self._play_btn = _Btn(
            (_cx(bw_lg), 330, bw_lg, 50),
            "P L A Y",
            self._f_btn,
            bg=COL_BLUE,
            hover=COL_LAVENDER,
            fg=COL_BASE,
        )
        self._load_btn = _Btn(
            (_cx(bw_lg), 394, bw_lg, 42),
            "S T U D Y",
            self._f_btn_sm,
            bg=COL_YELLOW,
            hover=(255, 240, 200),
            fg=COL_BASE,
        )
        self._hs_btn = _Btn(
            (_cx(bw_lg), 450, bw_lg, 42),
            "HIGH SCORES",
            self._f_btn_sm,
        )
        self._quit_btn = _Btn(
            (_cx(bw_lg), 506, bw_lg, 42),
            "Q U I T",
            self._f_btn_sm,
            bg=COL_RED,
            hover=(255, 170, 185),
            fg=COL_BASE,
        )

        self._menu_all: list[_Btn] = [
            *self._size_btns.values(),
            self._play_btn,
            self._load_btn,
            self._hs_btn,
            self._quit_btn,
        ]

    def _build_score_btns(self) -> None:
        self._score_back = _Btn(
            (_cx(180), WIN_H - 64, 180, 46), "B A C K", self._f_btn_sm
        )

    def _build_win_btns(self) -> None:
        bw = 220
        self._win_again = _Btn(
            (_cx(bw), 420, bw, 50),
            "PLAY AGAIN",
            self._f_btn,
            bg=COL_GREEN,
            hover=(190, 240, 190),
            fg=COL_BASE,
        )
        self._win_menu = _Btn(
            (_cx(bw), 488, bw, 46), "M E N U", self._f_btn_sm
        )

    def _build_game_btns(self) -> None:
        """Build in-game action buttons (placed below the board)."""
        bw, gap = 110, 10

        if self._study_mode:
            total = 3 * bw + 2 * gap
            sx = _cx(total)
            self._scramble_btn = _Btn(
                (sx, 0, bw, 36), "SCRAMBLE (R)", self._f_btn_sm,
                bg=COL_PINK, hover=(245, 210, 227), fg=COL_BASE,
            )
            self._hint_btn = _Btn(
                (sx + bw + gap, 0, bw, 36), "HINT (N)", self._f_btn_sm,
                bg=COL_YELLOW, hover=(255, 240, 200), fg=COL_BASE,
            )
            self._solve_btn = _Btn(
                (sx + 2 * (bw + gap), 0, bw, 36), "SOLVE (V)", self._f_btn_sm,
                bg=COL_GREEN, hover=(190, 240, 190), fg=COL_BASE,
            )
            self._game_action_btns = [self._scramble_btn, self._hint_btn, self._solve_btn]
        else:
            sx = _cx(bw)
            self._hint_btn = _Btn(
                (sx, 0, bw, 36), "HINT (N)", self._f_btn_sm,
                bg=COL_YELLOW, hover=(255, 240, 200), fg=COL_BASE,
            )
            self._scramble_btn = None
            self._solve_btn = None
            self._game_action_btns = [self._hint_btn]

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _tile_layout(self) -> tuple[int, int, int, int]:
        """Return (tile_px, origin_x, origin_y, total_px) for current game."""
        sz = self._game.size  # type: ignore[union-attr]
        tile_px = (BOARD_MAX - (sz + 1) * TILE_GAP) // sz
        total = sz * tile_px + (sz + 1) * TILE_GAP
        ox = _cx(total) + TILE_GAP
        oy = 76 + TILE_GAP
        return tile_px, ox, oy, total

    def _tile_rect(
        self, r: int, c: int, tpx: int, ox: int, oy: int
    ) -> pygame.Rect:
        return pygame.Rect(
            ox + c * (tpx + TILE_GAP),
            oy + r * (tpx + TILE_GAP),
            tpx,
            tpx,
        )

    # ── image tile preparation ───────────────────────────────────────────────

    _REF_SIZE = 64  # reference thumbnail side length in px

    def _prepare_tile_images(self) -> None:
        """Pick a random puzzle image and slice it into per-tile surfaces."""
        self._tile_images = {}
        self._ref_image = None
        if not self._images_dir.is_dir():
            return
        images = list(self._images_dir.glob("*.png"))
        if not images:
            return

        img_path = random.choice(images)
        full_img = pygame.image.load(str(img_path)).convert()

        # Reference thumbnail (from original high-res image)
        self._ref_image = pygame.transform.smoothscale(
            full_img, (self._REF_SIZE, self._REF_SIZE)
        )

        sz = self._game.size  # type: ignore[union-attr]
        tpx = (BOARD_MAX - (sz + 1) * TILE_GAP) // sz
        total_px = sz * tpx

        # Badge font for number overlays
        self._f_badge = pygame.font.SysFont(
            "Helvetica", max(10, tpx // 5), bold=True
        )

        # Scale image to fit the board area
        full_img = pygame.transform.smoothscale(full_img, (total_px, total_px))

        for val in range(1, sz * sz):
            # Tile value v maps to grid position ((v-1)//sz, (v-1)%sz) in the
            # solved state — crop the corresponding piece from the image.
            tr = (val - 1) // sz
            tc = (val - 1) % sz
            tile_surf = full_img.subsurface(
                pygame.Rect(tc * tpx, tr * tpx, tpx, tpx)
            ).copy()
            self._tile_images[val] = tile_surf

    # ── drawing ─────────────────────────────────────────────────────────────

    def _draw_menu(self) -> None:
        self._surf.fill(COL_BASE)

        _blit_center(
            self._surf,
            self._f_big.render("SLIDING  PUZZLE", True, COL_TEXT),
            80,
        )
        _blit_center(
            self._surf,
            self._f_body.render("Select difficulty", True, COL_SUBTEXT),
            210,
        )

        for s, btn in self._size_btns.items():
            btn.bg = COL_GREEN if s == self._sel_size else COL_SURFACE0
            btn.fg = COL_BASE if s == self._sel_size else COL_TEXT
            btn.draw(self._surf)

        self._play_btn.draw(self._surf)
        self._load_btn.draw(self._surf)
        self._hs_btn.draw(self._surf)
        self._quit_btn.draw(self._surf)

    def _draw_game(self) -> None:
        self._surf.fill(COL_BASE)
        game = self._game
        assert game is not None
        board = game.state.board
        sz = game.size
        tpx, ox, oy, total = self._tile_layout()
        f_tile = pygame.font.SysFont(
            "Helvetica", max(14, tpx // 3), bold=True
        )

        # header
        if self._study_mode:
            _blit_center(
                self._surf,
                self._f_title.render(
                    f"Study  {sz}\u00d7{sz}", True, COL_YELLOW
                ),
                14,
            )
        else:
            _blit_center(
                self._surf,
                self._f_title.render(
                    f"Sliding Puzzle  {sz}\u00d7{sz}", True, COL_TEXT
                ),
                14,
            )
            _blit_center(
                self._surf,
                self._f_body.render(
                    f"Moves: {game.state.moves}    "
                    f"Time: {self._fmt(game.state.elapsed_time)}",
                    True,
                    COL_PINK,
                ),
                44,
            )

        # board bg
        pygame.draw.rect(
            self._surf,
            COL_MANTLE,
            pygame.Rect(_cx(total), 76, total, total),
            border_radius=10,
        )

        # tiles
        for r in range(sz):
            for c in range(sz):
                val = board.tiles[r][c]
                if val == 0:
                    continue
                rect = self._tile_rect(r, c, tpx, ox, oy)
                if val in self._tile_images:
                    self._surf.blit(self._tile_images[val], rect.topleft)
                    # number badge overlay
                    num_lbl = self._f_badge.render(str(val), True, (255, 255, 255))
                    bw = num_lbl.get_width() + 8
                    bh = num_lbl.get_height() + 4
                    badge = pygame.Surface((bw, bh), pygame.SRCALPHA)
                    badge.fill((0, 0, 0, 150))
                    badge.blit(num_lbl, (4, 2))
                    self._surf.blit(badge, (rect.x + 2, rect.y + 2))
                    # green border for correct tiles
                    if board.is_tile_correct(r, c):
                        pygame.draw.rect(
                            self._surf, COL_GREEN, rect, width=3, border_radius=4
                        )
                else:
                    col = COL_GREEN if board.is_tile_correct(r, c) else COL_BLUE
                    pygame.draw.rect(self._surf, col, rect, border_radius=6)
                    lbl = f_tile.render(str(val), True, COL_BASE)
                    self._surf.blit(
                        lbl,
                        (
                            rect.centerx - lbl.get_width() // 2,
                            rect.centery - lbl.get_height() // 2,
                        ),
                    )

        # reference image thumbnail (top-right)
        if self._ref_image is not None:
            rs = self._REF_SIZE
            rx = WIN_W - rs - MARGIN
            ry = 8
            pygame.draw.rect(
                self._surf, COL_SURFACE1,
                pygame.Rect(rx - 2, ry - 2, rs + 4, rs + 4),
                border_radius=6,
            )
            self._surf.blit(self._ref_image, (rx, ry))
            ref_lbl = self._f_small.render("Ref", True, COL_SUBTEXT)
            self._surf.blit(
                ref_lbl, (rx + (rs - ref_lbl.get_width()) // 2, ry + rs + 4)
            )

        # action buttons row
        btn_y = 76 + total + 10
        for btn in self._game_action_btns:
            btn.rect.y = btn_y
            btn.draw(self._surf)

        # status message
        if self._status_msg:
            _blit_center(
                self._surf,
                self._f_small.render(self._status_msg, True, COL_YELLOW),
                btn_y + 44,
            )
            footer_y = btn_y + 64
        else:
            footer_y = btn_y + 44

        # footer hints
        if self._study_mode:
            hint_text = (
                "Arrows / WASD  move     R  scramble"
                "     M  menu     Esc  quit"
            )
        else:
            hint_text = (
                "Arrows / WASD  move     R  restart"
                "     M  menu     Esc  quit"
            )
        _blit_center(
            self._surf,
            self._f_small.render(hint_text, True, COL_OVERLAY0),
            footer_y,
        )

    def _draw_win(self) -> None:
        self._surf.fill(COL_BASE)
        game = self._game
        assert game is not None

        _blit_center(
            self._surf,
            self._f_big.render("\u2605  S O L V E D  \u2605", True, COL_GREEN),
            100,
        )

        info = [
            (f"Grid:   {game.size}\u00d7{game.size}", COL_SUBTEXT),
            (f"Moves:  {game.state.moves}", COL_YELLOW),
            (f"Time:   {self._fmt(game.state.elapsed_time)}", COL_YELLOW),
        ]
        y = 200
        for txt, col in info:
            _blit_center(self._surf, self._f_title.render(txt, True, col), y)
            y += 44

        self._win_again.draw(self._surf)
        self._win_menu.draw(self._surf)

    def _draw_scores(self) -> None:
        self._surf.fill(COL_BASE)
        _blit_center(
            self._surf,
            self._f_big.render("HIGH  SCORES", True, COL_TEXT),
            24,
        )

        self._hs = HighScoreManager(self._data_dir / "highscores.json")
        sizes = self._hs.get_all_sizes()
        y = 90

        if not sizes:
            _blit_center(
                self._surf,
                self._f_body.render("No high scores yet.", True, COL_OVERLAY0),
                y + 30,
            )
        else:
            for sz in sizes:
                _blit_center(
                    self._surf,
                    self._f_btn_sm.render(
                        f"\u2014  {sz}\u00d7{sz}  \u2014", True, COL_BLUE
                    ),
                    y,
                )
                y += 28
                for i, e in enumerate(self._hs.get_scores(sz)[:5], 1):
                    row = f"{i}.  {e.moves} moves   {e.time:.1f}s   ({e.date})"
                    self._surf.blit(
                        self._f_score.render(row, True, COL_SUBTEXT), (60, y)
                    )
                    y += 22
                y += 14
                if y > WIN_H - 90:
                    break

        self._score_back.draw(self._surf)

    # ── event handling ──────────────────────────────────────────────────────

    def _ev_menu(self, ev: pygame.event.Event) -> bool:
        if ev.type == pygame.MOUSEMOTION:
            for b in self._menu_all:
                b.motion(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for s, b in self._size_btns.items():
                if b.hit(ev.pos):
                    self._sel_size = s
                    return True
            if self._play_btn.hit(ev.pos):
                self._start_game()
            elif self._load_btn.hit(ev.pos):
                self._open_study()
            elif self._hs_btn.hit(ev.pos):
                self._screen = _Screen.SCORES
            elif self._quit_btn.hit(ev.pos):
                return False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                self._start_game()
            elif ev.key == pygame.K_l:
                self._open_study()
            elif ev.key in (pygame.K_q, pygame.K_ESCAPE):
                return False
        return True

    def _ev_game(self, ev: pygame.event.Event) -> bool:
        game = self._game
        assert game is not None
        if ev.type == pygame.MOUSEMOTION:
            for btn in self._game_action_btns:
                btn.motion(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # Check action buttons first
            if self._study_mode and self._scramble_btn and self._scramble_btn.hit(ev.pos):
                self._do_scramble()
                return True
            if self._hint_btn.hit(ev.pos):
                self._do_hint()
                return True
            if self._study_mode and self._solve_btn and self._solve_btn.hit(ev.pos):
                self._do_solve()
                return True
            # Then check tiles
            tpx, ox, oy, _ = self._tile_layout()
            for r in range(game.size):
                for c in range(game.size):
                    if self._tile_rect(r, c, tpx, ox, oy).collidepoint(ev.pos):
                        if game.state.board.tiles[r][c] != 0:
                            game.move_tile(r, c)
                            self._status_msg = ""
                        return True
        elif ev.type == pygame.KEYDOWN:
            _dirs = {
                pygame.K_UP: Direction.UP,
                pygame.K_w: Direction.UP,
                pygame.K_DOWN: Direction.DOWN,
                pygame.K_s: Direction.DOWN,
                pygame.K_LEFT: Direction.LEFT,
                pygame.K_a: Direction.LEFT,
                pygame.K_RIGHT: Direction.RIGHT,
                pygame.K_d: Direction.RIGHT,
            }
            if ev.key in _dirs:
                game.move(_dirs[ev.key])
                self._status_msg = ""
            elif ev.key == pygame.K_n:
                self._do_hint()
            elif ev.key == pygame.K_v and self._study_mode:
                self._do_solve()
            elif ev.key == pygame.K_r:
                if self._study_mode:
                    self._do_scramble()
                else:
                    self._start_game()
            elif ev.key == pygame.K_m:
                self._screen = _Screen.MENU
            elif ev.key == pygame.K_ESCAPE:
                self._screen = _Screen.MENU
        return True

    def _ev_win(self, ev: pygame.event.Event) -> bool:
        if ev.type == pygame.MOUSEMOTION:
            self._win_again.motion(ev.pos)
            self._win_menu.motion(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._win_again.hit(ev.pos):
                self._start_game()
            elif self._win_menu.hit(ev.pos):
                self._screen = _Screen.MENU
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_r, pygame.K_RETURN):
                self._start_game()
            elif ev.key in (pygame.K_m, pygame.K_ESCAPE):
                self._screen = _Screen.MENU
        return True

    def _ev_scores(self, ev: pygame.event.Event) -> bool:
        if ev.type == pygame.MOUSEMOTION:
            self._score_back.motion(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._score_back.hit(ev.pos):
                self._screen = _Screen.MENU
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (
                pygame.K_ESCAPE,
                pygame.K_BACKSPACE,
                pygame.K_m,
            ):
                self._screen = _Screen.MENU
        return True

    # ── solver actions ──────────────────────────────────────────────────────

    def _do_hint(self) -> None:
        game = self._game
        assert game is not None
        hint = Solver.hint(game.state.board)
        if hint is None:
            self._status_msg = (
                "Already solved!" if game.state.board.is_solved()
                else "No hint (unsolvable or solver not implemented)"
            )
        else:
            game.move(hint)
            self._status_msg = f"Hint: {hint.value}"

    def _do_solve(self) -> None:
        game = self._game
        assert game is not None
        try:
            moves = Solver.solve(game.state.board)
        except NotImplementedError:
            self._status_msg = "Solver not yet implemented"
            return

        if not moves:
            self._status_msg = (
                "Already solved!" if game.state.board.is_solved()
                else "Board is unsolvable"
            )
            return

        # Animate moves
        for i, direction in enumerate(moves):
            game.move(direction)
            self._status_msg = f"Solving… {i + 1}/{len(moves)}"
            self._draw_game()
            pygame.display.flip()
            pygame.event.pump()  # keep OS happy
            time.sleep(0.05)

        self._status_msg = f"Solved in {len(moves)} moves!"

    def _do_scramble(self) -> None:
        from backend.engine.gamegenerator import GameGenerator as GG
        board = GG.generate(self._sel_size)
        self._game = GamePlay.from_board(board)
        self._won = False
        self._status_msg = "Scrambled!"

    def _open_study(self) -> None:
        """Enter study mode — starts from solved board."""
        from backend.engine.gamegenerator import GameGenerator as GG
        self._study_mode = True
        board = GG.solved(self._sel_size)
        self._game = GamePlay.from_board(board)
        self._won = False
        self._status_msg = ""
        self._build_game_btns()
        self._prepare_tile_images()
        self._screen = _Screen.PLAYING

    # ── game state ──────────────────────────────────────────────────────────

    def _start_game(self) -> None:
        self._game = GamePlay(self._sel_size)
        self._won = False
        self._study_mode = False
        self._status_msg = ""
        self._build_game_btns()
        self._prepare_tile_images()
        self._screen = _Screen.PLAYING

    def _check_win(self) -> None:
        game = self._game
        if game is None or self._won or not game.is_won:
            return
        self._won = True
        game.state.pause()
        self._hs.add_score(
            game.size,
            HighScoreEntry(
                moves=game.state.moves,
                time=round(game.state.elapsed_time, 2),
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        self._build_win_btns()
        self._screen = _Screen.WIN

    # ── main loop ───────────────────────────────────────────────────────────

    def run_loop(self) -> None:
        _dispatch = {
            _Screen.MENU: self._ev_menu,
            _Screen.PLAYING: self._ev_game,
            _Screen.WIN: self._ev_win,
            _Screen.SCORES: self._ev_scores,
        }
        _draw = {
            _Screen.MENU: self._draw_menu,
            _Screen.PLAYING: self._draw_game,
            _Screen.WIN: self._draw_win,
            _Screen.SCORES: self._draw_scores,
        }

        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                    break
                handler = _dispatch.get(self._screen)
                if handler and not handler(ev):
                    running = False
                    break

            if self._screen == _Screen.PLAYING and not self._study_mode:
                self._check_win()

            drawer = _draw.get(self._screen)
            if drawer:
                drawer()
            pygame.display.flip()
            self._clock.tick(30)

        pygame.quit()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run(size: int = 3, data_dir: Path = Path("data")) -> None:
    """Launch the Pygame GUI (opens directly to the menu)."""
    app = PygameApp(size, data_dir)
    app.run_loop()
