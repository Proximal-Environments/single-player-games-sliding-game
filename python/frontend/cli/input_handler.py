"""Cross-platform single-keypress reader for CLI frontends.

Handles arrow keys, WASD, and special keys without requiring Enter.
Works on macOS / Linux (tty+termios) and Windows (msvcrt).
"""

from __future__ import annotations

import os
import sys


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


def get_key() -> str:
    """Read a single keypress and return a normalised action string.

    Possible return values:
        "up", "down", "left", "right"  — movement
        "quit"                         — q / Ctrl-C / Escape
        "restart"                      — r
        "help"                         — h / ?
        ""                             — unrecognised key
    """
    ch = _getch()

    # Arrow keys (Unix escape sequences: ESC [ A/B/C/D)
    if ch == "\x1b":
        ch2 = _getch()
        if ch2 == "[":
            ch3 = _getch()
            return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(
                ch3, ""
            )
        return "quit"  # bare Escape

    mapping: dict[str, str] = {
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
    }
    return mapping.get(ch, "")
