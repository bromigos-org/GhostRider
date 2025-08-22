"""Simple tests to verify basic functionality."""

from datetime import datetime

from ghostwriter.models import (
    MessageAuthor,
    MessageMetadata,
    MessagePlatform,
    MessagePriority,
    UnifiedMessage,
)
from ghostwriter.processor import MessageProcessor


def test_processor_creation() -> None:
    """Test that processor can be created."""
    processor = MessageProcessor()
    assert processor is not None


def test_priority_classification_urgent() -> None:
    """Test urgent priority classification."""
    processor = MessageProcessor()

    message = UnifiedMessage(
        id="test_1",
        platform=MessagePlatform.SMS,
        content="urgent help needed",
        timestamp=datetime.now(),
        author=MessageAuthor(id="test", name="Test User"),
        metadata=MessageMetadata(platform=MessagePlatform.SMS, message_id="test_1"),
    )

    priority, score = processor._classify_priority(message)
    assert priority == MessagePriority.URGENT
    assert score >= 0.8


def test_context_tags() -> None:
    """Test context tag extraction."""
    processor = MessageProcessor()

    message = UnifiedMessage(
        id="test_2",
        platform=MessagePlatform.SMS,
        content="meeting tomorrow with payment info",
        timestamp=datetime.now(),
        author=MessageAuthor(id="test", name="Test User"),
        metadata=MessageMetadata(platform=MessagePlatform.SMS, message_id="test_2"),
    )

    tags = processor._extract_context_tags(message)
    assert "platform:sms" in tags
    assert "meeting" in tags
    assert "financial" in tags


def test_models_work() -> None:
    """Test that models can be created and used."""
    author = MessageAuthor(id="1", name="Test")
    metadata = MessageMetadata(platform=MessagePlatform.SMS, message_id="123")

    message = UnifiedMessage(
        id="test",
        platform=MessagePlatform.SMS,
        content="test message",
        timestamp=datetime.now(),
        author=author,
        metadata=metadata,
    )

    assert message.platform == MessagePlatform.SMS
    assert message.priority == MessagePriority.MEDIUM  # default
    assert not message.processed  # default
