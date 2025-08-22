"""Database models for Discord data storage."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DiscordToken(BaseModel):
    """Discord OAuth token storage."""

    user_id: str  # Discord user ID
    access_token: str  # Encrypted access token
    refresh_token: str  # Encrypted refresh token
    expires_at: datetime  # Token expiration timestamp
    scope: str  # OAuth scopes granted
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DiscordChannel(BaseModel):
    """Discord channel information."""

    channel_id: str  # Discord channel ID
    name: str | None = None  # Channel name (None for DMs)
    channel_type: int  # Discord channel type (0=guild text, 1=DM, 3=group DM, etc.)
    recipient_ids: list[str] = Field(default_factory=list)  # For DMs/group DMs
    guild_id: str | None = None  # Guild ID if channel is in a guild
    last_fetched: datetime | None = None  # Last time messages were fetched
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DiscordMessage(BaseModel):
    """Discord message storage."""

    message_id: str  # Discord message ID
    channel_id: str  # Discord channel ID
    author_id: str  # Discord user ID of author
    author_name: str  # Display name of author
    author_avatar: str | None = None  # Avatar URL
    content: str  # Message content
    timestamp: datetime  # Message timestamp
    edited_timestamp: datetime | None = None  # Last edit timestamp
    message_type: int = 0  # Discord message type
    attachments: list[dict[str, Any]] = Field(default_factory=list)  # Attachment data
    embeds: list[dict[str, Any]] = Field(default_factory=list)  # Embed data
    mentions: list[str] = Field(default_factory=list)  # User IDs mentioned
    reply_to: str | None = None  # Message ID this is replying to
    raw_data: dict[str, Any] = Field(default_factory=dict)  # Full Discord message object
    processed: bool = False  # Whether message was processed by GhostRider
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }