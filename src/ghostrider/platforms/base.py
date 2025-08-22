"""Base platform interface for message integrations."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime

from ..models import MessageBatch, MessagePlatform, UnifiedMessage


class BaseMessagePlatform(ABC):
    """Base class for message platform integrations."""

    def __init__(self, platform_name: str):
        """Initialize the platform."""
        self.platform_name = platform_name
        self.is_running = False

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the platform."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""

    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send a message through the platform."""

    @abstractmethod
    async def receive_messages(self) -> list[UnifiedMessage]:
        """Receive new messages from the platform."""

    @abstractmethod
    async def get_message_history(self, limit: int = 50, since: datetime | None = None) -> list[UnifiedMessage]:
        """Get message history from the platform."""

    async def start_receiving(self, callback: Callable[[MessageBatch], Awaitable[None]] | None = None) -> None:
        """Start receiving messages continuously."""
        self.is_running = True
        while self.is_running:
            try:
                messages = await self.receive_messages()
                if messages and callback:
                    # Convert platform name to enum
                    platform_enum = MessagePlatform(self.platform_name)
                    batch = MessageBatch(
                        messages=messages,
                        batch_id=f"{self.platform_name}_{datetime.now().timestamp()}",
                        platform=platform_enum,
                        timestamp=datetime.now(),
                        total_count=len(messages),
                    )
                    await callback(batch)
            except Exception as e:
                print(f"Error receiving messages from {self.platform_name}: {e}")
                await asyncio.sleep(5)  # Wait before retrying
            else:
                await asyncio.sleep(1)  # Short delay between checks

    async def stop_receiving(self) -> None:
        """Stop receiving messages."""
        self.is_running = False
