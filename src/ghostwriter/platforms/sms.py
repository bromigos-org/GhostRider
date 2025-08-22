"""TextBee SMS platform integration."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

import requests  # type: ignore
from pydantic import BaseModel

from ..models import (
    MessageAuthor,
    MessageBatch,
    MessageMetadata,
    MessagePlatform,
    MessageType,
    SMSMetadata,
    UnifiedMessage,
)
from .base import BaseMessagePlatform


class TextBeeConfig(BaseModel):
    """Configuration for TextBee SMS platform."""

    api_key: str
    device_id: str
    base_url: str = "https://api.textbee.dev/api/v1"
    polling_interval: int = 10  # seconds


class TextBeeSMSMessage(BaseModel):
    """TextBee SMS message format."""

    id: str
    message: str
    phone: str
    timestamp: datetime
    direction: str  # 'received' or 'sent'


class TextBeeSMSPlatform(BaseMessagePlatform):
    """TextBee SMS platform integration."""

    def __init__(self, config: TextBeeConfig):
        """Initialize TextBee SMS platform."""
        super().__init__("sms")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": config.api_key, "Content-Type": "application/json"})
        self.processed_message_ids: set[str] = set()
        self.is_running: bool = False

    async def connect(self) -> None:
        """Connect to TextBee API (verify credentials)."""
        try:
            # Test API connection by attempting to get received SMS (validates credentials and device)
            url = f"{self.config.base_url}/gateway/devices/{self.config.device_id}/get-received-sms"
            response = self.session.get(url, timeout=10)  # Add timeout
            response.raise_for_status()
            print(f"Connected to TextBee SMS platform with device {self.config.device_id}")
        except requests.exceptions.Timeout:
            raise ConnectionError("Failed to connect to TextBee API: Connection timeout") from None
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to TextBee API: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from TextBee API."""
        self.session.close()
        print("Disconnected from TextBee SMS platform")

    async def send_message(self, recipient: str, content: str) -> bool:
        """Send SMS message via TextBee."""
        try:
            url = f"{self.config.base_url}/gateway/devices/{self.config.device_id}/send-sms"
            payload = {"recipients": [recipient], "message": content}

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            return bool(result.get("success", False))

        except requests.exceptions.RequestException as e:
            print(f"Failed to send SMS to {recipient}: {e}")
            return False

    async def receive_messages(self) -> list[UnifiedMessage]:
        """Receive new SMS messages from TextBee."""
        try:
            url = f"{self.config.base_url}/gateway/devices/{self.config.device_id}/get-received-sms"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            # The API returns messages in the 'data' field, not 'messages'
            messages = data.get("data", [])

            unified_messages = []
            for msg_data in messages:
                # Skip already processed messages
                msg_id = str(msg_data.get("_id", ""))
                if msg_id in self.processed_message_ids:
                    continue

                try:
                    unified_msg = self._convert_to_unified_message(msg_data)
                    unified_messages.append(unified_msg)
                    self.processed_message_ids.add(msg_id)
                except Exception as e:
                    print(f"❌ Error converting SMS message {msg_id}: {e}")
                    continue

            return unified_messages

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to receive SMS messages: {e}")
            return []

    async def get_message_history(self, limit: int = 50, since: datetime | None = None) -> list[UnifiedMessage]:
        """Get SMS message history from TextBee."""
        # Note: TextBee API may have different endpoints for history
        # For now, we'll use the same receive endpoint
        return await self.receive_messages()

    def _convert_to_unified_message(self, sms_data: dict) -> UnifiedMessage:
        """Convert TextBee SMS data to unified message format."""

        # Extract SMS data using the actual API field names
        message_id = str(sms_data.get("_id", ""))
        content = sms_data.get("message", "")
        phone = sms_data.get("sender", "")  # API uses 'sender' not 'phone'
        timestamp_str = sms_data.get("receivedAt", "")  # API uses 'receivedAt'

        # Parse timestamp
        try:
            if isinstance(timestamp_str, int | float):
                timestamp = datetime.fromtimestamp(timestamp_str / 1000)
            else:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            timestamp = datetime.now()

        # Create author (phone number as contact)
        author = MessageAuthor(id=phone, name=phone, phone=phone)  # Use phone as name for now

        # Create metadata
        metadata = MessageMetadata(platform=MessagePlatform.SMS, message_id=message_id, raw_data=sms_data)

        # Create SMS specific metadata
        sms_metadata = SMSMetadata(device_id=self.config.device_id, phone_number=phone)

        # Create unified message
        return UnifiedMessage(
            id=f"sms_{message_id}",
            platform=MessagePlatform.SMS,
            content=content,
            message_type=MessageType.TEXT,
            timestamp=timestamp,
            author=author,
            metadata=metadata,
            sms_metadata=sms_metadata,
        )

    async def start_polling(self, callback: Callable[[MessageBatch], Awaitable[None]] | None = None) -> None:
        """Start polling for SMS messages."""
        print(f"Starting SMS polling every {self.config.polling_interval} seconds")
        self.is_running = True

        while self.is_running:
            try:
                messages = await self.receive_messages()
                if messages and callback:
                    batch = MessageBatch(
                        messages=messages,
                        batch_id=f"sms_{datetime.now().timestamp()}",
                        platform=MessagePlatform.SMS,
                        timestamp=datetime.now(),
                        total_count=len(messages),
                    )
                    await callback(batch)

            except Exception as e:
                print(f"Error during SMS polling: {e}")

            await asyncio.sleep(self.config.polling_interval)

    def stop_polling(self) -> None:
        """Stop SMS polling."""
        self.is_running = False
        print("Stopped SMS polling")
