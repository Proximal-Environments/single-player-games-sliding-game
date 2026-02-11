"""High score persistence and management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HighScoreEntry:
    moves: int
    time: float
    date: str


class HighScoreManager:
    """Loads, saves, and queries high scores from a JSON file."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self._scores: dict[str, list[HighScoreEntry]] = {}
        self._load()

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if self.filepath.exists():
            data = json.loads(self.filepath.read_text())
            for size_key, entries in data.items():
                self._scores[size_key] = [
                    HighScoreEntry(**e) for e in entries
                ]

    def save(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, list[dict]] = {}
        for size_key, entries in self._scores.items():
            data[size_key] = [
                {"moves": e.moves, "time": e.time, "date": e.date}
                for e in entries
            ]
        self.filepath.write_text(json.dumps(data, indent=2) + "\n")

    # -- queries --------------------------------------------------------------

    def add_score(self, size: int, entry: HighScoreEntry) -> None:
        key = str(size)
        if key not in self._scores:
            self._scores[key] = []
        self._scores[key].append(entry)
        self._scores[key].sort(key=lambda e: (e.moves, e.time))
        self.save()

    def get_scores(self, size: int) -> list[HighScoreEntry]:
        return self._scores.get(str(size), [])

    def get_all_sizes(self) -> list[int]:
        return sorted(int(k) for k in self._scores)
