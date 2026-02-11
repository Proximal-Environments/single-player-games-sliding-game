"""Pygame GUI frontend — fully self-contained.

Includes main menu, difficulty selection, gameplay, win screen,
and high-score display.  No terminal interaction required.
"""

from __future__ import annotations

import enum
from datetime import datetime
from pathlib import Path

import pygame

from backend.engine.gameplay import GamePlay
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
        self._sel_size = max(3, min(8, default_size))

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

        # Pre-build buttons that don't move
        self._build_menu_btns()
        self._build_score_btns()

    # ── menu buttons ────────────────────────────────────────────────────────

    def _build_menu_btns(self) -> None:
        bw, bh = 72, 46
        sizes = [3, 4, 5, 6, 7, 8]
        cols = 4
        gap = 12
        row_w = cols * bw + (cols - 1) * gap
        sx = _cx(row_w)

        self._size_btns: dict[int, _Btn] = {}
        for idx, s in enumerate(sizes):
            r, c = divmod(idx, cols)
            x = sx + c * (bw + gap)
            y = 270 + r * (bh + gap)
            self._size_btns[s] = _Btn(
                (x, y, bw, bh),
                f"{s}\u00d7{s}",
                self._f_btn_sm,
            )

        bw_lg = 220
        self._play_btn = _Btn(
            (_cx(bw_lg), 410, bw_lg, 52),
            "P L A Y",
            self._f_btn,
            bg=COL_BLUE,
            hover=COL_LAVENDER,
            fg=COL_BASE,
        )
        self._hs_btn = _Btn(
            (_cx(bw_lg), 480, bw_lg, 46),
            "HIGH SCORES",
            self._f_btn_sm,
        )
        self._quit_btn = _Btn(
            (_cx(bw_lg), 542, bw_lg, 46),
            "Q U I T",
            self._f_btn_sm,
            bg=COL_RED,
            hover=(255, 170, 185),
            fg=COL_BASE,
        )

        self._menu_all: list[_Btn] = [
            *self._size_btns.values(),
            self._play_btn,
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
            self._f_body.render("Select grid size", True, COL_SUBTEXT),
            228,
        )

        for s, btn in self._size_btns.items():
            btn.bg = COL_GREEN if s == self._sel_size else COL_SURFACE0
            btn.fg = COL_BASE if s == self._sel_size else COL_TEXT
            btn.draw(self._surf)

        self._play_btn.draw(self._surf)
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

        # footer hints
        _blit_center(
            self._surf,
            self._f_small.render(
                "Arrows / WASD  move     R  restart"
                "     M  menu     Esc  quit",
                True,
                COL_OVERLAY0,
            ),
            76 + total + 14,
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
            elif self._hs_btn.hit(ev.pos):
                self._screen = _Screen.SCORES
            elif self._quit_btn.hit(ev.pos):
                return False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                self._start_game()
            elif ev.key in (pygame.K_q, pygame.K_ESCAPE):
                return False
        return True

    def _ev_game(self, ev: pygame.event.Event) -> bool:
        game = self._game
        assert game is not None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            tpx, ox, oy, _ = self._tile_layout()
            for r in range(game.size):
                for c in range(game.size):
                    if self._tile_rect(r, c, tpx, ox, oy).collidepoint(ev.pos):
                        if game.state.board.tiles[r][c] != 0:
                            game.move_tile(r, c)
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
            elif ev.key == pygame.K_r:
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

    # ── game state ──────────────────────────────────────────────────────────

    def _start_game(self) -> None:
        self._game = GamePlay(self._sel_size)
        self._won = False
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

            if self._screen == _Screen.PLAYING:
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
def run(size: int = 4, data_dir: Path = Path("data")) -> None:
    """Launch the Pygame GUI (opens directly to the menu)."""
    app = PygameApp(size, data_dir)
    app.run_loop()
