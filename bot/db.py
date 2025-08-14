
import aiosqlite
from typing import Optional, List, Tuple, Any
from .models import Track

DB_PATH = "data/db.sqlite3"

CREATE_SQL = '''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS tracks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  mode TEXT NOT NULL,           -- 'steam' | 'any'
  currency TEXT NOT NULL,       -- 'RUB' | 'USD'
  target_price_cents INTEGER NOT NULL,
  steam_appid INTEGER,
  last_price_cents INTEGER,
  last_notified_price_cents INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_checked_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tracks_user ON tracks(user_id);
CREATE INDEX IF NOT EXISTS idx_tracks_mode ON tracks(mode);
'''

async def init_db():
    import os
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_SQL)
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await db.commit()

async def add_track(user_id: int, title: str, url: str | None, mode: str, currency: str,
                    target_price_cents: int, steam_appid: int | None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tracks(user_id, title, url, mode, currency, target_price_cents, steam_appid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, title, url, mode, currency, target_price_cents, steam_appid),
        )
        await db.commit()
        return cur.lastrowid

async def list_tracks(user_id: int) -> list[Track]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM tracks WHERE user_id=? ORDER BY id", (user_id,)
        )
        rows = await cur.fetchall()
        return [Track(**dict(r)) for r in rows]

async def get_all_tracks() -> list[Track]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tracks ORDER BY id")
        rows = await cur.fetchall()
        return [Track(**dict(r)) for r in rows]

async def update_track_price(track_id: int, price_cents: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tracks SET last_price_cents=?, last_checked_at=CURRENT_TIMESTAMP WHERE id=?",
                         (price_cents, track_id))
        await db.commit()

async def mark_notified(track_id: int, price_cents: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tracks SET last_notified_price_cents=? WHERE id=?", (price_cents, track_id))
        await db.commit()

async def remove_track(user_id: int, track_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM tracks WHERE id=? AND user_id=?", (track_id, user_id))
        await db.commit()
        return cur.rowcount > 0
