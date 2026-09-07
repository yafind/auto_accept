from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
    is_banned BOOLEAN DEFAULT 0, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_request_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS channels (
    channel_id INTEGER PRIMARY KEY, username TEXT, link TEXT,
    is_active BOOLEAN DEFAULT 1, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'declined', 'expired')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, approved_at TIMESTAMP,
    declined_at TIMESTAMP, expires_at TIMESTAMP, processing_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id), FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, user_id INTEGER,
    channel_id INTEGER, details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS applications_pending_idx ON applications(status, expires_at);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.executescript(SCHEMA)
        try:
            await self.connection.execute("ALTER TABLE applications ADD COLUMN processing_at TIMESTAMP")
        except aiosqlite.OperationalError:
            pass
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    async def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        assert self.connection is not None
        cursor = await self.connection.execute(query, parameters)
        await self.connection.commit()
        return cursor

    async def fetchone(self, query: str, parameters: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        assert self.connection is not None
        async with self.connection.execute(query, parameters) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, parameters: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        assert self.connection is not None
        async with self.connection.execute(query, parameters) as cursor:
            return await cursor.fetchall()

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        await self.execute(
            "INSERT INTO users(user_id, username, first_name, last_request_at) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, last_request_at=excluded.last_request_at",
            (user_id, username, first_name, utc_now()),
        )

    async def sync_channels(self, channels: list[Any]) -> None:
        channel_ids = [channel.channel_id for channel in channels]
        if channel_ids:
            placeholders = ",".join("?" for _ in channel_ids)
            await self.execute(
                f"UPDATE channels SET is_active=0 WHERE channel_id NOT IN ({placeholders})",
                tuple(channel_ids),
            )
        else:
            await self.execute("UPDATE channels SET is_active=0")
        for channel in channels:
            await self.execute(
                "INSERT INTO channels(channel_id, username, link) VALUES(?, ?, ?) "
                "ON CONFLICT(channel_id) DO UPDATE SET username=excluded.username, link=excluded.link, is_active=1",
                (channel.channel_id, channel.display_name, channel.link),
            )

    async def is_banned(self, user_id: int) -> bool:
        row = await self.fetchone("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
        return bool(row and row["is_banned"])

    async def is_channel_active(self, channel_id: int) -> bool:
        row = await self.fetchone("SELECT is_active FROM channels WHERE channel_id=?", (channel_id,))
        return bool(row and row["is_active"])

    async def create_application(self, user_id: int, channel_id: int, expires_at: datetime) -> int:
        cursor = await self.execute(
            "INSERT INTO applications(user_id, channel_id, status, expires_at) VALUES(?, ?, 'pending', ?)",
            (user_id, channel_id, expires_at.isoformat(sep=" ")),
        )
        return cursor.lastrowid

    async def get_application(self, application_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM applications WHERE id=?", (application_id,))

    async def get_pending_application(self, user_id: int, channel_id: int) -> aiosqlite.Row | None:
        return await self.fetchone(
            "SELECT * FROM applications WHERE user_id=? AND channel_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (user_id, channel_id),
        )

    async def claim_application(self, application_id: int, timeout_seconds: int = 120) -> bool:
        stale_before = utc_now().timestamp() - timeout_seconds
        stale_datetime = datetime.fromtimestamp(stale_before, timezone.utc).replace(tzinfo=None)
        cursor = await self.execute(
            "UPDATE applications SET processing_at=? "
            "WHERE id=? AND status='pending' AND (processing_at IS NULL OR processing_at < ?)",
            (utc_now(), application_id, stale_datetime),
        )
        return cursor.rowcount == 1

    async def release_application(self, application_id: int) -> None:
        await self.execute(
            "UPDATE applications SET processing_at=NULL WHERE id=? AND status='pending'",
            (application_id,),
        )

    async def approve_application(self, application_id: int) -> bool:
        cursor = await self.execute(
            "UPDATE applications SET status='approved', approved_at=?, processing_at=NULL "
            "WHERE id=? AND status='pending' AND processing_at IS NOT NULL",
            (utc_now(), application_id),
        )
        return cursor.rowcount == 1

    async def expire_application(self, application_id: int) -> bool:
        cursor = await self.execute(
            "UPDATE applications SET status='expired', declined_at=?, processing_at=NULL "
            "WHERE id=? AND status='pending' AND processing_at IS NOT NULL",
            (utc_now(), application_id),
        )
        return cursor.rowcount == 1

    async def pending_expired(self) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM applications WHERE status='pending' AND processing_at IS NULL AND expires_at < ?",
            (utc_now(),),
        )

    async def log(self, event_type: str, user_id: int | None = None, channel_id: int | None = None, details: str = "") -> None:
        await self.execute(
            "INSERT INTO logs(event_type, user_id, channel_id, details) VALUES(?, ?, ?, ?)",
            (event_type, user_id, channel_id, details),
        )

    async def set_banned(self, user_id: int, banned: bool) -> None:
        await self.execute(
            "INSERT INTO users(user_id, is_banned) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET is_banned=excluded.is_banned",
            (user_id, int(banned)),
        )

    async def stats(self, date: str | None = None) -> list[aiosqlite.Row]:
        where = "WHERE date(created_at) = date(?)" if date else ""
        parameters = (date,) if date else ()
        return await self.fetchall(
            f"SELECT status, COUNT(*) AS count FROM applications {where} GROUP BY status",
            parameters,
        )

    async def active_channels(self) -> list[aiosqlite.Row]:
        return await self.fetchall("SELECT * FROM channels WHERE is_active=1 ORDER BY username")
