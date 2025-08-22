"""Database manager for SQLite operations."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
from cryptography.fernet import Fernet

from .models import DiscordChannel, DiscordMessage, DiscordToken


class DatabaseManager:
    """Manages SQLite database operations for Discord data."""

    def __init__(self, db_path: str | Path = "ghostwriter.db", encryption_key: bytes | None = None):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

    async def initialize(self) -> None:
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Discord tokens table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS discord_tokens (
                    user_id TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Discord channels table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS discord_channels (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT,
                    channel_type INTEGER NOT NULL,
                    recipient_ids TEXT,
                    guild_id TEXT,
                    last_fetched TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Discord messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS discord_messages (
                    message_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_avatar TEXT,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    edited_timestamp TEXT,
                    message_type INTEGER DEFAULT 0,
                    attachments TEXT,
                    embeds TEXT,
                    mentions TEXT,
                    reply_to TEXT,
                    raw_data TEXT,
                    processed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (channel_id) REFERENCES discord_channels (channel_id)
                )
            """)

            # Create indexes for better query performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp ON discord_messages (channel_id, timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_processed ON discord_messages (processed)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_last_fetched ON discord_channels (last_fetched)")

            await db.commit()

    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for storage."""
        return self.cipher.encrypt(token.encode()).decode()

    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a stored token."""
        return self.cipher.decrypt(encrypted_token.encode()).decode()

    async def store_discord_token(self, token: DiscordToken) -> None:
        """Store Discord OAuth token."""
        encrypted_access = self._encrypt_token(token.access_token)
        encrypted_refresh = self._encrypt_token(token.refresh_token)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO discord_tokens 
                (user_id, access_token, refresh_token, expires_at, scope, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                token.user_id,
                encrypted_access,
                encrypted_refresh,
                token.expires_at.isoformat(),
                token.scope,
                token.created_at.isoformat(),
                datetime.now().isoformat(),
            ))
            await db.commit()

    async def get_discord_token(self, user_id: str) -> DiscordToken | None:
        """Retrieve Discord OAuth token."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, access_token, refresh_token, expires_at, scope, created_at, updated_at
                FROM discord_tokens WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                return DiscordToken(
                    user_id=row[0],
                    access_token=self._decrypt_token(row[1]),
                    refresh_token=self._decrypt_token(row[2]),
                    expires_at=datetime.fromisoformat(row[3]),
                    scope=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                )

    async def store_discord_channel(self, channel: DiscordChannel) -> None:
        """Store Discord channel information."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO discord_channels 
                (channel_id, name, channel_type, recipient_ids, guild_id, last_fetched, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                channel.channel_id,
                channel.name,
                channel.channel_type,
                json.dumps(channel.recipient_ids),
                channel.guild_id,
                channel.last_fetched.isoformat() if channel.last_fetched else None,
                channel.created_at.isoformat(),
                datetime.now().isoformat(),
            ))
            await db.commit()

    async def get_discord_channels(self) -> list[DiscordChannel]:
        """Get all Discord channels."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT channel_id, name, channel_type, recipient_ids, guild_id, last_fetched, created_at, updated_at
                FROM discord_channels
                ORDER BY updated_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                channels = []
                for row in rows:
                    channels.append(DiscordChannel(
                        channel_id=row[0],
                        name=row[1],
                        channel_type=row[2],
                        recipient_ids=json.loads(row[3] or "[]"),
                        guild_id=row[4],
                        last_fetched=datetime.fromisoformat(row[5]) if row[5] else None,
                        created_at=datetime.fromisoformat(row[6]),
                        updated_at=datetime.fromisoformat(row[7]),
                    ))
                return channels

    async def store_discord_message(self, message: DiscordMessage) -> None:
        """Store Discord message."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO discord_messages 
                (message_id, channel_id, author_id, author_name, author_avatar, content, timestamp,
                 edited_timestamp, message_type, attachments, embeds, mentions, reply_to, raw_data, processed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.channel_id,
                message.author_id,
                message.author_name,
                message.author_avatar,
                message.content,
                message.timestamp.isoformat(),
                message.edited_timestamp.isoformat() if message.edited_timestamp else None,
                message.message_type,
                json.dumps(message.attachments),
                json.dumps(message.embeds),
                json.dumps(message.mentions),
                message.reply_to,
                json.dumps(message.raw_data),
                int(message.processed),
                message.created_at.isoformat(),
            ))
            await db.commit()

    async def get_discord_messages(self, channel_id: str, limit: int = 50) -> list[DiscordMessage]:
        """Get Discord messages for a channel."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT message_id, channel_id, author_id, author_name, author_avatar, content, timestamp,
                       edited_timestamp, message_type, attachments, embeds, mentions, reply_to, raw_data, processed, created_at
                FROM discord_messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (channel_id, limit)) as cursor:
                rows = await cursor.fetchall()
                messages = []
                for row in rows:
                    messages.append(DiscordMessage(
                        message_id=row[0],
                        channel_id=row[1],
                        author_id=row[2],
                        author_name=row[3],
                        author_avatar=row[4],
                        content=row[5],
                        timestamp=datetime.fromisoformat(row[6]),
                        edited_timestamp=datetime.fromisoformat(row[7]) if row[7] else None,
                        message_type=row[8],
                        attachments=json.loads(row[9] or "[]"),
                        embeds=json.loads(row[10] or "[]"),
                        mentions=json.loads(row[11] or "[]"),
                        reply_to=row[12],
                        raw_data=json.loads(row[13] or "{}"),
                        processed=bool(row[14]),
                        created_at=datetime.fromisoformat(row[15]),
                    ))
                return messages

    async def mark_messages_processed(self, message_ids: list[str]) -> None:
        """Mark messages as processed."""
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ",".join("?" * len(message_ids))
            await db.execute(f"""
                UPDATE discord_messages 
                SET processed = 1 
                WHERE message_id IN ({placeholders})
            """, message_ids)
            await db.commit()

    async def update_channel_last_fetched(self, channel_id: str, timestamp: datetime) -> None:
        """Update the last fetched timestamp for a channel."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE discord_channels 
                SET last_fetched = ?, updated_at = ?
                WHERE channel_id = ?
            """, (timestamp.isoformat(), datetime.now().isoformat(), channel_id))
            await db.commit()