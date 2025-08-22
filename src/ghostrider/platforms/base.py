"""Base platform interface for message integrations."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from ..models import MessageBatch, UnifiedMessage


class MessagePlatform(ABC):
    """Base class for message platform integrations."""
    
    def __init__(self, platform_name: str):
        """Initialize the platform."""
        self.platform_name = platform_name
        self.is_running = False
        
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the platform."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        pass
    
    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send a message through the platform."""
        pass
    
    @abstractmethod
    async def receive_messages(self) -> List[UnifiedMessage]:
        """Receive new messages from the platform."""
        pass
    
    @abstractmethod
    async def get_message_history(
        self, 
        limit: int = 50, 
        since: Optional[datetime] = None
    ) -> List[UnifiedMessage]:
        """Get message history from the platform."""
        pass
    
    async def start_receiving(self, callback=None) -> None:
        """Start receiving messages continuously."""
        self.is_running = True
        while self.is_running:
            try:
                messages = await self.receive_messages()
                if messages and callback:
                    batch = MessageBatch(
                        messages=messages,
                        batch_id=f"{self.platform_name}_{datetime.now().timestamp()}",
                        platform=self.platform_name,
                        timestamp=datetime.now(),
                        total_count=len(messages)
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