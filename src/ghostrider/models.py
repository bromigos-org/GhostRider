"""Unified message models for GhostRider."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
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
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class MessageMetadata(BaseModel):
    """Platform-specific message metadata."""
    
    platform: MessagePlatform
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    thread_id: Optional[str] = None
    message_id: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class SMSMetadata(BaseModel):
    """SMS-specific metadata."""
    
    device_id: str
    phone_number: str
    carrier: Optional[str] = None
    sim_slot: Optional[int] = None


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
    context_tags: List[str] = Field(default_factory=list)
    
    # Attachments and media
    attachments: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)
    
    # Platform metadata
    metadata: MessageMetadata
    
    # SMS specific fields
    sms_metadata: Optional[SMSMetadata] = None
    
    # Processing status
    processed: bool = False
    processing_timestamp: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        
        use_enum_values = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


class MessageBatch(BaseModel):
    """Batch of messages for processing."""
    
    messages: List[UnifiedMessage]
    batch_id: str
    platform: MessagePlatform
    timestamp: datetime
    total_count: int
    
    @property
    def unprocessed_messages(self) -> List[UnifiedMessage]:
        """Get unprocessed messages from the batch."""
        return [msg for msg in self.messages if not msg.processed]


class MessageProcessingResult(BaseModel):
    """Result of message processing."""
    
    message_id: str
    success: bool
    priority_assigned: MessagePriority
    urgency_score: float
    context_tags: List[str]
    processing_time_ms: float
    error: Optional[str] = None