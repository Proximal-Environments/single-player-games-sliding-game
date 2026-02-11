"""Cross-platform single-keypress reader for CLI frontends.

Handles arrow keys, WASD, and special keys without requiring Enter.
Works on macOS / Linux (tty+termios) and Windows (msvcrt).
"""

from __future__ import annotations

import os
import sys


# -- low-level character readers -----------------------------------------------


def _getch_unix() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def _getch_windows() -> str:
    import msvcrt  # type: ignore[import-not-found]

    return msvcrt.getch().decode("utf-8", errors="ignore")


_getch = _getch_windows if os.name == "nt" else _getch_unix


# -- shared key mapping --------------------------------------------------------

_KEY_MAP: dict[str, str] = {
    "w": "up",
    "W": "up",
    "s": "down",
    "S": "down",
    "a": "left",
    "A": "left",
    "d": "right",
    "D": "right",
    "q": "quit",
    "Q": "quit",
    "\x03": "quit",  # Ctrl-C
    "r": "restart",
    "R": "restart",
    "h": "help",
    "?": "help",
    "v": "solve",
    "V": "solve",
    "n": "hint",
    "N": "hint",
    "p": "print",
    "P": "print",
    "\r": "enter",
    "\n": "enter",
}

_ARROW_MAP: dict[str, str] = {
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
}


def _resolve(ch: str) -> str:
    """Map a raw character to its action string."""
    return _KEY_MAP.get(ch, ch if ch.isprintable() else "")


# -- public API ----------------------------------------------------------------


def get_key() -> str:
    """Read a single keypress and return a normalised action string.

    Blocks until a key is pressed.

    Possible return values:
        "up", "down", "left", "right"  — movement
        "quit"                         — q / Ctrl-C / Escape
        "restart"                      — r
        "help"                         — h / ?
        "solve"                        — v (auto-solve)
        "hint"                         — n (next best move)
        "print"                        — p (export board state)
        "enter"                        — Enter / Return
        "<char>"                       — unmapped printable char
        ""                             — unrecognised key
    """
    ch = _getch()

    # Arrow keys (Unix escape sequences: ESC [ A/B/C/D)
    if ch == "\x1b":
        ch2 = _getch()
        if ch2 == "[":
            ch3 = _getch()
            return _ARROW_MAP.get(ch3, "")
        return "quit"  # bare Escape

    return _resolve(ch)


def get_key_timeout(timeout: float) -> str | None:
    """Read a single keypress with a timeout.

    Returns the normalised action string (same as ``get_key``) or
    ``None`` if no key was pressed within *timeout* seconds.

    Uses ``os.read`` (unbuffered) so that ``select`` accurately
    reflects pending bytes — required for multi-byte escape sequences
    (arrow keys).
    """
    if os.name == "nt":
        import msvcrt  # type: ignore[import-not-found]
        import time as _time

        end = _time.monotonic() + timeout
        while _time.monotonic() < end:
            if msvcrt.kbhit():
                return get_key()
            _time.sleep(0.02)
        return None

    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None

        # Use os.read (unbuffered) so subsequent select() calls see
        # remaining bytes of multi-byte sequences (e.g. arrow keys).
        ch = os.read(fd, 1).decode("utf-8", errors="ignore")

        # Arrow keys: ESC [ A/B/C/D
        if ch == "\x1b":
            r2, _, _ = select.select([fd], [], [], 0.1)
            if r2:
                ch2 = os.read(fd, 1).decode("utf-8", errors="ignore")
                if ch2 == "[":
                    r3, _, _ = select.select([fd], [], [], 0.1)
                    if r3:
                        ch3 = os.read(fd, 1).decode("utf-8", errors="ignore")
                        return _ARROW_MAP.get(ch3, "")
                    return ""
                return "quit"
            return "quit"  # bare Escape

        return _resolve(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
