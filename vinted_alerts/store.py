"""SQLite storage for seen listings and per-watch price history."""

from __future__ import annotations

import sqlite3
import statistics
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    watch TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    price REAL NOT NULL,
    title TEXT,
    url TEXT,
    seen_at REAL NOT NULL,
    alerted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (watch, item_id)
);
CREATE INDEX IF NOT EXISTS seen_watch_time ON seen (watch, seen_at);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def is_seen(self, watch: str, item_id: int) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM seen WHERE watch = ? AND item_id = ?", (watch, item_id)).fetchone()
        return row is not None

    def has_history(self, watch: str) -> bool:
        return self.db.execute("SELECT 1 FROM seen WHERE watch = ? LIMIT 1", (watch,)).fetchone() is not None

    def add(self, watch: str, item_id: int, price: float, title: str, url: str,
            alerted: bool = False) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO seen VALUES (?, ?, ?, ?, ?, ?, ?)",
            (watch, item_id, price, title, url, time.time(), int(alerted)))
        self.db.commit()

    def recent_prices(self, watch: str, limit: int = 300) -> list[float]:
        rows = self.db.execute(
            "SELECT price FROM seen WHERE watch = ? ORDER BY seen_at DESC LIMIT ?",
            (watch, limit)).fetchall()
        return [r[0] for r in rows]

    def median_price(self, watch: str, limit: int = 300) -> tuple[float | None, int]:
        prices = self.recent_prices(watch, limit)
        return (statistics.median(prices) if prices else None), len(prices)

    def stats(self) -> list[tuple]:
        return self.db.execute(
            "SELECT watch, COUNT(*), MIN(price), AVG(price), SUM(alerted) "
            "FROM seen GROUP BY watch ORDER BY watch").fetchall()

    def close(self) -> None:
        self.db.close()
