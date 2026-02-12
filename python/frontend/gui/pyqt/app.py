"""PyQt6 GUI frontend — fully self-contained.

Includes main menu, difficulty selection, gameplay, win screen,
and high-score display.  No terminal interaction required.
"""

from __future__ import annotations

import random
import sys
import time as _time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QKeyEvent, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from backend.engine.gameplay import GamePlay
from backend.engine.gamesolver import Solver
from backend.models.board import Direction
from backend.models.highscore import HighScoreEntry, HighScoreManager

# ---------------------------------------------------------------------------
# Catppuccin Mocha CSS colours
# ---------------------------------------------------------------------------
_BASE = "#1e1e2e"
_MANTLE = "#181825"
_SURFACE0 = "#313244"
_SURFACE1 = "#45475a"
_OVERLAY0 = "#6c7086"
_TEXT = "#cdd6f4"
_SUBTEXT = "#a6adc8"
_BLUE = "#89b4fa"
_BLUE_H = "#a4c4fc"
_GREEN = "#a6e3a1"
_GREEN_H = "#b8ecb4"
_PINK = "#f5c2e7"
_YELLOW = "#f9e2af"
_RED = "#f38ba8"
_RED_H = "#f5a0b8"
_LAVENDER = "#b4befe"

_GLOBAL_CSS = f"""
    QMainWindow, QWidget#page {{ background: {_BASE}; }}
    QLabel {{ color: {_TEXT}; }}
"""


def _styled_btn(
    text: str,
    *,
    bg: str = _SURFACE0,
    hover: str = _SURFACE1,
    fg: str = _TEXT,
    font_size: int = 14,
    bold: bool = True,
    min_w: int = 0,
    min_h: int = 44,
    radius: int = 8,
) -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(QFont("Helvetica", font_size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    btn.setMinimumHeight(min_h)
    if min_w:
        btn.setMinimumWidth(min_w)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton {{ background:{bg}; color:{fg};"
        f" border:none; border-radius:{radius}px; padding:6px 18px; }}"
        f" QPushButton:hover {{ background:{hover}; }}"
    )
    return btn


# ═══════════════════════════════════════════════════════════════════════════
# Pages
# ═══════════════════════════════════════════════════════════════════════════


class _MenuPage(QWidget):
    """Main menu with size selection, play, scores, quit."""

    _DIFFICULTIES: list[tuple[str, int]] = [
        ("Easy 3\u00d73", 3),
        ("Medium 7\u00d77", 7),
        ("Hard 10\u00d710", 10),
        ("V.Hard 12\u00d712", 12),
    ]

    def __init__(self, default_size: int = 3) -> None:
        super().__init__()
        self.setObjectName("page")
        self.selected_size = default_size

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setSpacing(12)
        root.setContentsMargins(30, 30, 30, 30)

        # title
        title = QLabel("SLIDING  PUZZLE")
        title.setFont(QFont("Helvetica", 34, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        root.addSpacerItem(QSpacerItem(0, 24))

        # subtitle
        sub = QLabel("Select difficulty")
        sub.setFont(QFont("Helvetica", 15))
        sub.setStyleSheet(f"color:{_SUBTEXT};")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        root.addSpacerItem(QSpacerItem(0, 8))

        # difficulty buttons — single row
        self._size_btns: dict[int, QPushButton] = {}
        hbox = QHBoxLayout()
        hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hbox.setSpacing(10)
        for label, s in self._DIFFICULTIES:
            btn = _styled_btn(label, min_w=100, min_h=46, font_size=12)
            btn.clicked.connect(lambda _, sz=s: self._pick_size(sz))
            hbox.addWidget(btn)
            self._size_btns[s] = btn
        root.addLayout(hbox)

        root.addSpacerItem(QSpacerItem(0, 18))

        # action buttons
        self.play_btn = _styled_btn(
            "P L A Y", bg=_BLUE, hover=_LAVENDER, fg=_BASE,
            font_size=16, min_w=240, min_h=52,
        )
        root.addWidget(self.play_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addSpacerItem(QSpacerItem(0, 4))

        self.load_btn = _styled_btn(
            "S T U D Y", bg=_YELLOW, hover="#fcecc4", fg=_BASE,
            min_w=240, font_size=13,
        )
        root.addWidget(self.load_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addSpacerItem(QSpacerItem(0, 4))

        self.scores_btn = _styled_btn("HIGH SCORES", min_w=240, font_size=13)
        root.addWidget(self.scores_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addSpacerItem(QSpacerItem(0, 4))

        self.quit_btn = _styled_btn(
            "Q U I T", bg=_RED, hover=_RED_H, fg=_BASE, min_w=240, font_size=13
        )
        root.addWidget(self.quit_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._refresh_size_highlight()

    def _pick_size(self, s: int) -> None:
        self.selected_size = s
        self._refresh_size_highlight()

    def _refresh_size_highlight(self) -> None:
        for s, btn in self._size_btns.items():
            if s == self.selected_size:
                btn.setStyleSheet(
                    f"QPushButton {{ background:{_GREEN}; color:{_BASE};"
                    f" border:none; border-radius:8px; padding:6px 18px; font-weight:bold; }}"
                    f" QPushButton:hover {{ background:{_GREEN_H}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background:{_SURFACE0}; color:{_TEXT};"
                    f" border:none; border-radius:8px; padding:6px 18px; font-weight:bold; }}"
                    f" QPushButton:hover {{ background:{_SURFACE1}; }}"
                )


class _GamePage(QWidget):
    """The puzzle board with tile buttons and live stats."""

    def __init__(
        self, size: int, hs: HighScoreManager, images_dir: Path, *, study_mode: bool = False
    ) -> None:
        super().__init__()
        self.setObjectName("page")
        self._size = size
        self._hs = hs
        self._images_dir = images_dir
        self.study_mode = study_mode
        self.won = False

        # Study mode starts from solved board; game mode starts scrambled
        if study_mode:
            from backend.engine.gamegenerator import GameGenerator as GG
            board = GG.solved(size)
            self.game = GamePlay.from_board(board)
        else:
            self.game = GamePlay(size)

        tile_px = max(40, min(84, 400 // size))
        self._tile_px = tile_px
        f_sz = max(12, tile_px // 4)
        self._tile_pixmaps: dict[int, QPixmap] = {}
        self._ref_pixmap: QPixmap | None = None
        self._prepare_tile_images()

        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(16, 10, 16, 10)

        # title row with reference image
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.setSpacing(12)

        title_text = f"Study  {size}\u00d7{size}" if study_mode else f"Sliding Puzzle  {size}\u00d7{size}"
        t = QLabel(title_text)
        t.setFont(QFont("Helvetica", 17, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{_YELLOW};" if study_mode else f"color:{_TEXT};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(t)

        # reference thumbnail
        ref_side = min(48, tile_px)
        self._ref_label = QLabel()
        self._ref_label.setFixedSize(ref_side, ref_side)
        self._ref_label.setStyleSheet(
            f"border:2px solid {_SURFACE1}; border-radius:4px; background:{_MANTLE};"
        )
        if self._ref_pixmap is not None:
            self._ref_label.setPixmap(
                self._ref_pixmap.scaled(
                    ref_side, ref_side,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        title_row.addWidget(self._ref_label)

        root.addLayout(title_row)

        # stats — only in game mode
        self._stats: QLabel | None = None
        if not study_mode:
            self._stats = QLabel()
            self._stats.setFont(QFont("Helvetica", 13))
            self._stats.setStyleSheet(f"color:{_PINK};")
            self._stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(self._stats)

        # board
        frame = QFrame()
        frame.setStyleSheet(f"background:{_MANTLE}; border-radius:10px;")
        self._grid = QGridLayout(frame)
        self._grid.setSpacing(4)
        self._grid.setContentsMargins(8, 8, 8, 8)
        root.addWidget(frame, alignment=Qt.AlignmentFlag.AlignCenter)

        self._btns: list[list[QPushButton]] = []
        for r in range(size):
            row: list[QPushButton] = []
            for c in range(size):
                b = QPushButton()
                b.setFixedSize(tile_px, tile_px)
                b.setFont(QFont("Helvetica", f_sz, QFont.Weight.Bold))
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(lambda _, rr=r, cc=c: self._click(rr, cc))
                self._grid.addWidget(b, r, c)
                row.append(b)
            self._btns.append(row)

        # action buttons row
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(8)

        if study_mode:
            self.scramble_btn = _styled_btn(
                "Scramble (R)", bg=_PINK, hover="#f5d0e3", fg=_BASE,
                font_size=12, min_w=100, min_h=34,
            )
            btn_row.addWidget(self.scramble_btn)
            self.scramble_btn.clicked.connect(self._do_scramble)

        self.hint_btn = _styled_btn(
            "Hint (N)", bg=_YELLOW, hover="#fcecc4", fg=_BASE,
            font_size=12, min_w=90, min_h=34,
        )
        btn_row.addWidget(self.hint_btn)

        self.solve_btn: QPushButton | None = None
        if study_mode:
            self.solve_btn = _styled_btn(
                "Solve (V)", bg=_GREEN, hover=_GREEN_H, fg=_BASE,
                font_size=12, min_w=90, min_h=34,
            )
            btn_row.addWidget(self.solve_btn)

        root.addLayout(btn_row)

        # status
        self._status = QLabel("")
        self._status.setFont(QFont("Helvetica", 11))
        self._status.setStyleSheet(f"color:{_YELLOW};")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._status)

        # controls hint
        if study_mode:
            controls_text = (
                "Arrows / WASD  move     R  scramble     N  hint"
                "     V  solve     M  menu"
            )
        else:
            controls_text = (
                "Arrows / WASD  move     N  hint"
                "     R  restart     M  menu"
            )
        self._controls = QLabel(controls_text)
        self._controls.setFont(QFont("Helvetica", 10))
        self._controls.setStyleSheet(f"color:{_OVERLAY0};")
        self._controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._controls)

        # wire buttons
        self.hint_btn.clicked.connect(self._do_hint)
        if self.solve_btn is not None:
            self.solve_btn.clicked.connect(self._do_solve)

        # timer — only in game mode
        self._timer: QTimer | None = None
        if not study_mode:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(200)

        self._sync()

    # -- helpers --

    def _prepare_tile_images(self) -> None:
        """Pick a random puzzle image and slice it into per-tile pixmaps."""
        self._tile_pixmaps = {}
        self._ref_pixmap = None
        if not self._images_dir.is_dir():
            return
        images = list(self._images_dir.glob("*.png"))
        if not images:
            return

        img_path = random.choice(images)
        full_pm = QPixmap(str(img_path))
        if full_pm.isNull():
            return

        # Reference thumbnail (from original high-res pixmap)
        self._ref_pixmap = full_pm.scaled(
            64, 64,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        total_px = self._size * self._tile_px
        full_pm = full_pm.scaled(
            total_px, total_px,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        badge_font = QFont("Helvetica", max(8, self._tile_px // 6), QFont.Weight.Bold)

        for val in range(1, self._size * self._size):
            tr = (val - 1) // self._size
            tc = (val - 1) % self._size
            tile_pm = full_pm.copy(
                tc * self._tile_px, tr * self._tile_px,
                self._tile_px, self._tile_px,
            )

            # Paint number badge overlay onto each tile
            painter = QPainter(tile_pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setFont(badge_font)
            fm = painter.fontMetrics()
            text = str(val)
            tw = fm.horizontalAdvance(text)
            th = fm.height()
            # semi-transparent dark badge background
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(2, 2, tw + 8, th + 4, 3.0, 3.0)
            # white number text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(6, 2 + fm.ascent() + 2, text)
            painter.end()

            self._tile_pixmaps[val] = tile_pm

    def _sync(self) -> None:
        board = self.game.state.board
        for r in range(self._size):
            for c in range(self._size):
                v = board.tiles[r][c]
                b = self._btns[r][c]
                if v == 0:
                    b.setText("")
                    b.setIcon(QIcon())
                    b.setStyleSheet(
                        f"QPushButton{{background:{_MANTLE};border:none;border-radius:8px;}}"
                    )
                elif v in self._tile_pixmaps:
                    b.setText("")
                    b.setIcon(QIcon(self._tile_pixmaps[v]))
                    b.setIconSize(QSize(self._tile_px, self._tile_px))
                    border = (
                        f"border:3px solid {_GREEN};"
                        if board.is_tile_correct(r, c)
                        else "border:1px solid #2a2a3e;"
                    )
                    b.setStyleSheet(
                        f"QPushButton{{background:transparent;{border}"
                        f"border-radius:8px;padding:0px;}}"
                        f"QPushButton:hover{{opacity:0.9;}}"
                    )
                else:
                    b.setIcon(QIcon())
                    b.setText(str(v))
                    bg = _GREEN if board.is_tile_correct(r, c) else _BLUE
                    hv = _GREEN_H if board.is_tile_correct(r, c) else _BLUE_H
                    b.setStyleSheet(
                        f"QPushButton{{background:{bg};color:{_BASE};"
                        f"border:none;border-radius:8px;font-weight:bold;}}"
                        f"QPushButton:hover{{background:{hv};}}"
                    )
        if self._stats is not None:
            self._tick()

    def _tick(self) -> None:
        if self._stats is None:
            return
        m, s = divmod(int(self.game.state.elapsed_time), 60)
        self._stats.setText(
            f"Moves: {self.game.state.moves}    Time: {m:02d}:{s:02d}"
        )

    def _click(self, r: int, c: int) -> None:
        if self.won or self.game.state.board.tiles[r][c] == 0:
            return
        self.game.move_tile(r, c)
        self._status.setText("")
        self._sync()
        if not self.study_mode:
            self._check_win()

    def move(self, d: Direction) -> None:
        if self.won:
            return
        self.game.move(d)
        self._status.setText("")
        self._sync()
        if not self.study_mode:
            self._check_win()

    def restart(self) -> None:
        """Restart — scramble in study, new game in play."""
        if self.study_mode:
            self._do_scramble()
        else:
            self.game = GamePlay(self._size)
            self.won = False
            if self._timer is not None:
                self._timer.start(200)
            self._status.setText("")
            self._controls.setStyleSheet(f"color:{_OVERLAY0};")
            self._sync()

    # -- solver actions --

    def _do_scramble(self) -> None:
        from backend.engine.gamegenerator import GameGenerator as GG
        board = GG.generate(self._size)
        self.game = GamePlay.from_board(board)
        self.won = False
        self._status.setText("Scrambled!")
        self._sync()

    def _do_hint(self) -> None:
        if self.won:
            return
        hint = Solver.hint(self.game.state.board)
        if hint is None:
            self._status.setText(
                "Already solved!" if self.game.state.board.is_solved()
                else "No hint (unsolvable or solver not implemented)"
            )
        else:
            self.game.move(hint)
            self._status.setText(f"Hint: {hint.value}")
            self._sync()
            if not self.study_mode:
                self._check_win()

    def _do_solve(self) -> None:
        if self.won:
            return
        try:
            moves = Solver.solve(self.game.state.board)
        except NotImplementedError:
            self._status.setText("Solver not yet implemented")
            return

        if not moves:
            self._status.setText(
                "Already solved!" if self.game.state.board.is_solved()
                else "Board is unsolvable"
            )
            return

        for i, direction in enumerate(moves):
            self.game.move(direction)
            self._status.setText(f"Solving… {i + 1}/{len(moves)}")
            self._sync()
            QApplication.processEvents()
            _time.sleep(0.05)

        self._status.setText(f"Solved in {len(moves)} moves!")

    def _check_win(self) -> None:
        if self.won or not self.game.is_won:
            return
        self.won = True
        self.game.state.pause()
        if self._timer is not None:
            self._timer.stop()
        self._hs.add_score(
            self._size,
            HighScoreEntry(
                moves=self.game.state.moves,
                time=round(self.game.state.elapsed_time, 2),
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        self._controls.setText("Solved!   R  play again     M  menu")
        self._controls.setStyleSheet(f"color:{_GREEN};font-weight:bold;")
        # parent window listens via self.won flag


class _WinPage(QWidget):
    """Victory screen with stats and navigation buttons."""

    def __init__(self, size: int, moves: int, time_s: float) -> None:
        super().__init__()
        self.setObjectName("page")

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setSpacing(10)
        root.setContentsMargins(30, 30, 30, 30)

        star = QLabel("\u2605  S O L V E D  \u2605")
        star.setFont(QFont("Helvetica", 32, QFont.Weight.Bold))
        star.setStyleSheet(f"color:{_GREEN};")
        star.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(star)

        root.addSpacerItem(QSpacerItem(0, 20))

        for txt, col in [
            (f"Grid:   {size}\u00d7{size}", _SUBTEXT),
            (f"Moves:  {moves}", _YELLOW),
            (f"Time:   {_fmt(time_s)}", _YELLOW),
        ]:
            lbl = QLabel(txt)
            lbl.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{col};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(lbl)

        root.addSpacerItem(QSpacerItem(0, 24))

        self.again_btn = _styled_btn(
            "PLAY AGAIN", bg=_GREEN, hover=_GREEN_H, fg=_BASE,
            font_size=16, min_w=240, min_h=50,
        )
        root.addWidget(self.again_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addSpacerItem(QSpacerItem(0, 6))

        self.menu_btn = _styled_btn("M E N U", min_w=240, font_size=13)
        root.addWidget(self.menu_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class _ScoresPage(QWidget):
    """High-score display with a back button."""

    def __init__(self, hs: HighScoreManager) -> None:
        super().__init__()
        self.setObjectName("page")

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(24, 20, 24, 16)

        title = QLabel("HIGH  SCORES")
        title.setFont(QFont("Helvetica", 26, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # scrollable area for scores
        scroll_content = QWidget()
        scroll_content.setObjectName("page")
        vbox = QVBoxLayout(scroll_content)
        vbox.setSpacing(2)
        vbox.setContentsMargins(10, 10, 10, 10)

        sizes = hs.get_all_sizes()
        if not sizes:
            lbl = QLabel("No high scores yet.")
            lbl.setFont(QFont("Helvetica", 14))
            lbl.setStyleSheet(f"color:{_OVERLAY0};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(lbl)
        else:
            for sz in sizes:
                h = QLabel(f"\u2014  {sz}\u00d7{sz}  \u2014")
                h.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
                h.setStyleSheet(f"color:{_BLUE};")
                h.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vbox.addWidget(h)
                for i, e in enumerate(hs.get_scores(sz)[:5], 1):
                    row = QLabel(
                        f"  {i}.  {e.moves} moves   {e.time:.1f}s   ({e.date})"
                    )
                    row.setFont(QFont("Helvetica", 12))
                    row.setStyleSheet(f"color:{_SUBTEXT};")
                    vbox.addWidget(row)
                vbox.addSpacerItem(QSpacerItem(0, 10))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        scroll.setStyleSheet(
            f"QScrollArea {{ border:none; background:{_BASE}; }}"
        )
        root.addWidget(scroll)

        self.back_btn = _styled_btn("B A C K", min_w=200, font_size=13)
        root.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ═══════════════════════════════════════════════════════════════════════════
# Main window
# ═══════════════════════════════════════════════════════════════════════════

_IDX_MENU = 0
_IDX_GAME = 1
_IDX_WIN = 2
_IDX_SCORES = 3


def _fmt(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    return f"{m:02d}:{s:02d}"


class _MainWindow(QMainWindow):
    def __init__(self, default_size: int, data_dir: Path) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._images_dir = data_dir.parent / "assets" / "images"
        self._hs = HighScoreManager(data_dir / "highscores.json")

        self.setWindowTitle("Sliding Puzzle")
        self.setStyleSheet(_GLOBAL_CSS)
        self.setMinimumSize(480, 580)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # menu
        self._menu = _MenuPage(default_size)
        self._menu.play_btn.clicked.connect(self._on_play)
        self._menu.load_btn.clicked.connect(self._on_study)
        self._menu.scores_btn.clicked.connect(self._show_scores)
        self._menu.quit_btn.clicked.connect(self.close)
        self._stack.addWidget(self._menu)  # 0

        # placeholders (replaced dynamically)
        self._game_page: _GamePage | None = None
        self._stack.addWidget(QWidget())  # 1
        self._stack.addWidget(QWidget())  # 2

        # scores
        self._scores_page = _ScoresPage(self._hs)
        self._scores_page.back_btn.clicked.connect(self._show_menu)
        self._stack.addWidget(self._scores_page)  # 3

        self._stack.setCurrentIndex(_IDX_MENU)

    # -- navigation ---

    def _show_menu(self) -> None:
        self._stack.setCurrentIndex(_IDX_MENU)

    def _on_play(self, _checked: bool = False) -> None:
        """Start a normal game (hint only, scored)."""
        self._start_game_page(study_mode=False)

    def _on_study(self, _checked: bool = False) -> None:
        """Open study mode — starts from solved board with scramble button."""
        self._start_game_page(study_mode=True)

    def _start_game_page(self, *, study_mode: bool = False) -> None:
        size = self._menu.selected_size
        page = _GamePage(size, self._hs, self._images_dir, study_mode=study_mode)
        self._game_page = page

        old = self._stack.widget(_IDX_GAME)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(_IDX_GAME, page)
        self._stack.setCurrentIndex(_IDX_GAME)

    def _show_scores(self) -> None:
        self._hs = HighScoreManager(self._data_dir / "highscores.json")
        page = _ScoresPage(self._hs)
        page.back_btn.clicked.connect(self._show_menu)

        old = self._stack.widget(_IDX_SCORES)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(_IDX_SCORES, page)
        self._scores_page = page
        self._stack.setCurrentIndex(_IDX_SCORES)

    def _show_win(self) -> None:
        gp = self._game_page
        assert gp is not None
        page = _WinPage(gp._size, gp.game.state.moves, gp.game.state.elapsed_time)
        page.again_btn.clicked.connect(self._on_play)
        page.menu_btn.clicked.connect(self._show_menu)

        old = self._stack.widget(_IDX_WIN)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(_IDX_WIN, page)
        self._stack.setCurrentIndex(_IDX_WIN)

    # -- keyboard ---

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # noqa: N802
        if event is None:
            return
        key = event.key()
        idx = self._stack.currentIndex()

        if idx == _IDX_MENU:
            if key == Qt.Key.Key_Return:
                self._on_play()
            elif key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
                self.close()

        elif idx == _IDX_GAME and self._game_page is not None:
            gp = self._game_page
            _dirs = {
                Qt.Key.Key_Up: Direction.UP,
                Qt.Key.Key_W: Direction.UP,
                Qt.Key.Key_Down: Direction.DOWN,
                Qt.Key.Key_S: Direction.DOWN,
                Qt.Key.Key_Left: Direction.LEFT,
                Qt.Key.Key_A: Direction.LEFT,
                Qt.Key.Key_Right: Direction.RIGHT,
                Qt.Key.Key_D: Direction.RIGHT,
            }
            if key in _dirs:
                gp.move(_dirs[key])
                if gp.won and not gp.study_mode:
                    self._show_win()
            elif key == Qt.Key.Key_N:
                gp._do_hint()
                if gp.won and not gp.study_mode:
                    self._show_win()
            elif key == Qt.Key.Key_V and gp.study_mode:
                gp._do_solve()
            elif key == Qt.Key.Key_R:
                if gp.won and not gp.study_mode:
                    self._on_play()
                else:
                    gp.restart()
            elif key in (Qt.Key.Key_M, Qt.Key.Key_Escape):
                self._show_menu()

        elif idx == _IDX_WIN:
            if key in (Qt.Key.Key_R, Qt.Key.Key_Return):
                self._on_play()
            elif key in (Qt.Key.Key_M, Qt.Key.Key_Escape):
                self._show_menu()

        elif idx == _IDX_SCORES:
            if key in (
                Qt.Key.Key_Escape,
                Qt.Key.Key_Backspace,
                Qt.Key.Key_M,
            ):
                self._show_menu()

        else:
            super().keyPressEvent(event)

    # -- poll for win (mouse-based play) ---

    def _poll_win(self) -> None:
        gp = self._game_page
        if (
            gp is not None
            and gp.won
            and not gp.study_mode
            and self._stack.currentIndex() == _IDX_GAME
        ):
            self._show_win()

    def showEvent(self, ev) -> None:  # noqa: N802
        super().showEvent(ev)
        # periodic check for mouse-click wins
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_win)
        self._poll_timer.start(200)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run(size: int = 3, data_dir: Path = Path("data")) -> None:
    """Launch the PyQt6 GUI (opens directly to the menu)."""
    qapp = QApplication.instance() or QApplication(sys.argv)
    window = _MainWindow(size, data_dir)
    window.show()
    qapp.exec()
