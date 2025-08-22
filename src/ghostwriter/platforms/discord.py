"""Discord OAuth 2.0 platform integration."""

import asyncio
import base64
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from cryptography.fernet import Fernet

from ..config import DiscordConfig
from ..database import DatabaseManager, DiscordChannel, DiscordMessage, DiscordToken
from ..models import (
    MessageAuthor,
    MessageMetadata,
    MessagePlatform,
    MessageType,
    UnifiedMessage,
)
from .base import BaseMessagePlatform


class DiscordOAuthError(Exception):
    """Discord OAuth specific errors."""


class DiscordPlatform(BaseMessagePlatform):
    """Discord OAuth 2.0 platform integration."""

    def __init__(self, config: DiscordConfig):
        """Initialize Discord platform."""
        super().__init__("discord")
        self.config = config
        self.db_manager = DatabaseManager(
            db_path=config.db_path,
            encryption_key=self._get_encryption_key(),
        )
        self.session: aiohttp.ClientSession | None = None
        self.current_user_id: str | None = None

    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for tokens."""
        if self.config.encryption_key:
            return self.config.encryption_key.encode()
        return Fernet.generate_key()

    async def connect(self) -> None:
        """Initialize database and HTTP session."""
        await self.db_manager.initialize()
        self.session = aiohttp.ClientSession()
        print("Discord platform initialized")

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
        print("Disconnected from Discord platform")

    def generate_oauth_url(self, state: str | None = None) -> str:
        """Generate Discord OAuth 2.0 authorization URL."""
        if not self.config.client_id or not self.config.redirect_uri:
            raise DiscordOAuthError("Discord client_id and redirect_uri must be configured")

        # Required scopes for basic Discord OAuth
        scopes = ["identify", "guilds"]
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
        }
        
        if state:
            params["state"] = state
        else:
            params["state"] = secrets.token_urlsafe(32)

        query_string = urllib.parse.urlencode(params)
        return f"https://discord.com/oauth2/authorize?{query_string}"

    async def exchange_code_for_token(self, code: str) -> DiscordToken:
        """Exchange authorization code for access token."""
        if not self.session:
            raise DiscordOAuthError("Session not initialized")

        if not self.config.client_id or not self.config.client_secret or not self.config.redirect_uri:
            raise DiscordOAuthError("Discord OAuth configuration incomplete")

        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with self.session.post(
            f"{self.config.api_base_url}/oauth2/token",
            data=data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise DiscordOAuthError(f"Token exchange failed: {response.status} - {error_text}")

            token_data = await response.json()

        # Get user info to store user_id
        user_info = await self._get_current_user(token_data["access_token"])
        user_id = user_info["id"]

        # Create token object
        expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        token = DiscordToken(
            user_id=user_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            scope=token_data["scope"],
        )

        # Store token in database
        await self.db_manager.store_discord_token(token)
        self.current_user_id = user_id

        return token

    async def refresh_access_token(self, user_id: str) -> DiscordToken | None:
        """Refresh an expired access token."""
        if not self.session:
            raise DiscordOAuthError("Session not initialized")

        token = await self.db_manager.get_discord_token(user_id)
        if not token:
            return None

        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with self.session.post(
            f"{self.config.api_base_url}/oauth2/token",
            data=data,
            headers=headers,
        ) as response:
            if response.status != 200:
                return None

            token_data = await response.json()

        # Update token
        expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        updated_token = DiscordToken(
            user_id=user_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", token.refresh_token),
            expires_at=expires_at,
            scope=token_data["scope"],
        )

        await self.db_manager.store_discord_token(updated_token)
        return updated_token

    async def _get_valid_token(self, user_id: str) -> str | None:
        """Get a valid access token, refreshing if necessary."""
        token = await self.db_manager.get_discord_token(user_id)
        if not token:
            return None

        # Check if token is expired
        if datetime.now() >= token.expires_at:
            refreshed_token = await self.refresh_access_token(user_id)
            if not refreshed_token:
                return None
            return refreshed_token.access_token

        return token.access_token

    async def _make_api_request(self, endpoint: str, user_id: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Make authenticated API request to Discord."""
        if not self.session:
            return None

        access_token = await self._get_valid_token(user_id)
        if not access_token:
            return None

        headers = {"Authorization": f"Bearer {access_token}"}

        async with self.session.get(f"{self.config.api_base_url}{endpoint}", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:
                # Rate limited
                retry_after = int(response.headers.get("Retry-After", 1))
                print(f"Discord API rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                return await self._make_api_request(endpoint, user_id)
            else:
                print(f"Discord API error: {response.status} - {await response.text()}")
                return None

    async def _get_current_user(self, access_token: str) -> dict[str, Any]:
        """Get current user info."""
        if not self.session:
            raise DiscordOAuthError("Session not initialized")

        headers = {"Authorization": f"Bearer {access_token}"}

        async with self.session.get(f"{self.config.api_base_url}/users/@me", headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise DiscordOAuthError(f"Failed to get user info: {response.status} - {error_text}")
            return await response.json()

    async def get_user_channels(self, user_id: str) -> list[DiscordChannel]:
        """Get user's DM channels and accessible guild channels."""
        channels = []

        # Get DM channels
        dm_data = await self._make_api_request("/users/@me/channels", user_id)
        if dm_data:
            for channel_data in dm_data:
                channel = DiscordChannel(
                    channel_id=channel_data["id"],
                    name=None,  # DMs don't have names
                    channel_type=channel_data["type"],
                    recipient_ids=[r["id"] for r in channel_data.get("recipients", [])],
                )
                channels.append(channel)
                await self.db_manager.store_discord_channel(channel)

        return channels

    async def fetch_channel_messages(self, channel_id: str, user_id: str, limit: int = 10) -> list[DiscordMessage]:
        """Fetch recent messages from a channel."""
        endpoint = f"/channels/{channel_id}/messages?limit={limit}"
        messages_data = await self._make_api_request(endpoint, user_id)
        
        if not messages_data:
            return []

        messages = []
        for msg_data in messages_data:
            message = self._convert_to_discord_message(msg_data)
            messages.append(message)
            await self.db_manager.store_discord_message(message)

        # Update channel last fetched timestamp
        await self.db_manager.update_channel_last_fetched(channel_id, datetime.now())
        
        return messages

    def _convert_to_discord_message(self, msg_data: dict[str, Any]) -> DiscordMessage:
        """Convert Discord API message data to DiscordMessage."""
        author_data = msg_data.get("author", {})
        
        return DiscordMessage(
            message_id=msg_data["id"],
            channel_id=msg_data["channel_id"],
            author_id=author_data.get("id", ""),
            author_name=author_data.get("username", "Unknown"),
            author_avatar=author_data.get("avatar"),
            content=msg_data.get("content", ""),
            timestamp=datetime.fromisoformat(msg_data["timestamp"].replace("Z", "+00:00")),
            edited_timestamp=datetime.fromisoformat(msg_data["edited_timestamp"].replace("Z", "+00:00")) if msg_data.get("edited_timestamp") else None,
            message_type=msg_data.get("type", 0),
            attachments=msg_data.get("attachments", []),
            embeds=msg_data.get("embeds", []),
            mentions=[mention["id"] for mention in msg_data.get("mentions", [])],
            reply_to=msg_data.get("message_reference", {}).get("message_id"),
            raw_data=msg_data,
        )

    def _convert_to_unified_message(self, discord_msg: DiscordMessage) -> UnifiedMessage:
        """Convert DiscordMessage to UnifiedMessage."""
        author = MessageAuthor(
            id=discord_msg.author_id,
            name=discord_msg.author_name,
            avatar_url=f"https://cdn.discordapp.com/avatars/{discord_msg.author_id}/{discord_msg.author_avatar}.png" if discord_msg.author_avatar else None,
        )

        metadata = MessageMetadata(
            platform=MessagePlatform.DISCORD,
            channel_id=discord_msg.channel_id,
            message_id=discord_msg.message_id,
            raw_data=discord_msg.raw_data,
        )

        return UnifiedMessage(
            id=f"discord_{discord_msg.message_id}",
            platform=MessagePlatform.DISCORD,
            content=discord_msg.content,
            message_type=MessageType.TEXT,
            timestamp=discord_msg.timestamp,
            author=author,
            metadata=metadata,
            attachments=[att.get("url", "") for att in discord_msg.attachments],
            media_urls=[att.get("url", "") for att in discord_msg.attachments if att.get("content_type", "").startswith(("image/", "video/"))],
        )

    async def send_message(self, recipient: str, content: str) -> bool:
        """Send message to Discord channel."""
        # This would require additional OAuth scopes and implementation
        # For now, returning False as it's not implemented
        return False

    async def receive_messages(self) -> list[UnifiedMessage]:
        """Receive new messages from Discord."""
        if not self.current_user_id:
            return []

        # Get all channels and fetch recent messages
        channels = await self.get_user_channels(self.current_user_id)
        all_messages = []

        for channel in channels[:10]:  # Limit to 10 most recent conversations
            discord_messages = await self.fetch_channel_messages(
                channel.channel_id, 
                self.current_user_id,
                self.config.max_messages_per_channel
            )
            
            for discord_msg in discord_messages:
                if not discord_msg.processed:
                    unified_msg = self._convert_to_unified_message(discord_msg)
                    all_messages.append(unified_msg)

        return all_messages

    async def get_message_history(self, limit: int = 50, since: datetime | None = None) -> list[UnifiedMessage]:
        """Get Discord message history."""
        return await self.receive_messages()

    async def authenticate_user(self, auth_code: str) -> str:
        """Authenticate user with OAuth code and return user ID."""
        token = await self.exchange_code_for_token(auth_code)
        return token.user_id

    def get_oauth_url(self) -> str:
        """Get OAuth authorization URL."""
        return self.generate_oauth_url()