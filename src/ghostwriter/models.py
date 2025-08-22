"""Unified message models for GhostRider."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessagePlatform(str, Enum):
    """Supported messaging platforms."""

    SLACK = "slack"
    DISCORD = "discord"
    GMAIL = "gmail"
    SMS = "sms"


class MessagePriority(str, Enum):
    """Message priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(str, Enum):
    """Types of messages."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    LINK = "link"


class MessageAuthor(BaseModel):
    """Message author information."""

    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class MessageMetadata(BaseModel):
    """Platform-specific message metadata."""

    platform: MessagePlatform
    channel_id: str | None = None
    channel_name: str | None = None
    thread_id: str | None = None
    message_id: str
    raw_data: dict[str, Any] = Field(default_factory=dict)


class SMSMetadata(BaseModel):
    """SMS-specific metadata."""

    device_id: str
    phone_number: str
    carrier: str | None = None
    sim_slot: int | None = None


class UnifiedMessage(BaseModel):
    """Unified message schema for all platforms."""

    # Core message fields
    id: str
    platform: MessagePlatform
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime

    # Author information
    author: MessageAuthor

    # Priority and classification
    priority: MessagePriority = MessagePriority.MEDIUM
    urgency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    context_tags: list[str] = Field(default_factory=list)

    # Attachments and media
    attachments: list[str] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)

    # Platform metadata
    metadata: MessageMetadata

    # SMS specific fields
    sms_metadata: SMSMetadata | None = None

    # Processing status
    processed: bool = False
    processing_timestamp: datetime | None = None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


class MessageBatch(BaseModel):
    """Batch of messages for processing."""

    messages: list[UnifiedMessage]
    batch_id: str
    platform: MessagePlatform
    timestamp: datetime
    total_count: int

    @property
    def unprocessed_messages(self) -> list[UnifiedMessage]:
        """Get unprocessed messages from the batch."""
        return [msg for msg in self.messages if not msg.processed]


class MessageProcessingResult(BaseModel):
    """Result of message processing."""

    message_id: str
    success: bool
    priority_assigned: MessagePriority
    urgency_score: float
    context_tags: list[str]
    processing_time_ms: float
    error: str | None = None
