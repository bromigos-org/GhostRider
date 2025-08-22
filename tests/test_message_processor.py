"""Tests for message processing and priority classification."""

import pytest
from datetime import datetime
from ghostrider.processor import MessageProcessor
from ghostrider.models import (
    MessageBatch, 
    MessagePlatform, 
    MessagePriority,
    MessageAuthor,
    MessageMetadata,
    SMSMetadata,
    UnifiedMessage,
    MessageType
)


@pytest.fixture
def processor():
    """Create a message processor instance."""
    return MessageProcessor()


@pytest.fixture
def sample_message():
    """Create a sample unified message."""
    return UnifiedMessage(
        id="test_1",
        platform=MessagePlatform.SMS,
        content="This is a test message",
        message_type=MessageType.TEXT,
        timestamp=datetime.now(),
        author=MessageAuthor(
            id="+1234567890",
            name="Test User",
            phone="+1234567890"
        ),
        metadata=MessageMetadata(
            platform=MessagePlatform.SMS,
            message_id="test_1"
        ),
        sms_metadata=SMSMetadata(
            device_id="test_device",
            phone_number="+1234567890"
        )
    )


class TestMessageProcessor:
    """Test message processing and priority classification."""
    
    @pytest.mark.asyncio
    async def test_process_batch(self, processor, sample_message):
        """Test processing a batch of messages."""
        batch = MessageBatch(
            messages=[sample_message],
            batch_id="test_batch",
            platform=MessagePlatform.SMS,
            timestamp=datetime.now(),
            total_count=1
        )
        
        results = await processor.process_batch(batch)
        
        assert len(results) == 1
        result = results[0]
        
        assert result.message_id == "test_1"
        assert result.success is True
        assert result.priority_assigned in MessagePriority
        assert 0.0 <= result.urgency_score <= 1.0
        assert isinstance(result.context_tags, list)
        assert result.processing_time_ms > 0
        
        # Check message was marked as processed
        assert sample_message.processed is True
        assert sample_message.processing_timestamp is not None
    
    def test_classify_priority_urgent(self, processor, sample_message):
        """Test urgent priority classification."""
        sample_message.content = "URGENT: Server is down! Need help ASAP!"
        
        priority, urgency_score = processor._classify_priority(sample_message)
        
        assert priority == MessagePriority.URGENT
        assert urgency_score >= 0.8
    
    def test_classify_priority_high(self, processor, sample_message):
        """Test high priority classification."""
        sample_message.content = "Important meeting reminder for tomorrow"
        
        priority, urgency_score = processor._classify_priority(sample_message)
        
        assert priority == MessagePriority.HIGH
        assert 0.6 <= urgency_score < 0.8
    
    def test_classify_priority_low(self, processor, sample_message):
        """Test low priority classification."""
        sample_message.content = "FYI: Weekly newsletter update"
        
        priority, urgency_score = processor._classify_priority(sample_message)
        
        assert priority == MessagePriority.LOW
        assert urgency_score <= 0.3
    
    def test_classify_priority_medium_default(self, processor, sample_message):
        """Test medium priority as default."""
        sample_message.content = "Just a normal message with no special keywords"
        
        priority, urgency_score = processor._classify_priority(sample_message)
        
        assert priority == MessagePriority.MEDIUM
        assert 0.3 < urgency_score < 0.8
    
    def test_sms_specific_priority_rules(self, processor, sample_message):
        """Test SMS-specific priority rules."""
        # Short SMS should increase urgency
        sample_message.content = "Help!"
        
        priority, urgency_score = processor._classify_priority(sample_message)
        
        # Should be higher than base score due to short length
        base_message = sample_message.model_copy()
        base_message.content = "This is a much longer message that should not get the same urgency boost"
        base_priority, base_score = processor._classify_priority(base_message)
        
        # Short message should have higher urgency (though both might be same priority level)
        assert urgency_score >= base_score
    
    def test_time_based_urgency(self, processor, sample_message):
        """Test time-based urgency adjustment."""
        # Message at night (outside business hours)
        night_time = datetime(2024, 1, 1, 23, 0, 0)  # 11 PM
        sample_message.timestamp = night_time
        
        _, night_score = processor._classify_priority(sample_message)
        
        # Message during business hours
        day_time = datetime(2024, 1, 1, 14, 0, 0)  # 2 PM
        sample_message.timestamp = day_time
        
        _, day_score = processor._classify_priority(sample_message)
        
        # Night message should have higher urgency
        assert night_score >= day_score
    
    def test_extract_context_tags_platform(self, processor, sample_message):
        """Test platform context tag extraction."""
        tags = processor._extract_context_tags(sample_message)
        
        assert "platform:sms" in tags
    
    def test_extract_context_tags_meeting(self, processor, sample_message):
        """Test meeting context tag extraction."""
        sample_message.content = "Don't forget our Zoom meeting tomorrow at 2 PM"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "meeting" in tags
    
    def test_extract_context_tags_financial(self, processor, sample_message):
        """Test financial context tag extraction."""
        sample_message.content = "Your invoice payment of $500 is due today"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "financial" in tags
    
    def test_extract_context_tags_security(self, processor, sample_message):
        """Test security context tag extraction."""
        sample_message.content = "Reset your password using this secure login link"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "security" in tags
    
    def test_extract_context_tags_delivery(self, processor, sample_message):
        """Test delivery context tag extraction."""
        sample_message.content = "Your package has been shipped! Tracking: ABC123"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "delivery" in tags
    
    def test_extract_context_tags_url(self, processor, sample_message):
        """Test URL detection in context tags."""
        sample_message.content = "Check out this link: https://example.com"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "contains-link" in tags
    
    def test_extract_context_tags_phone(self, processor, sample_message):
        """Test phone number detection in context tags."""
        sample_message.content = "Call me at 555-123-4567 when you get this"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "contains-phone" in tags
    
    def test_extract_context_tags_time_sensitive(self, processor, sample_message):
        """Test time-sensitive tag extraction."""
        sample_message.content = "Need this done today ASAP!"
        
        tags = processor._extract_context_tags(sample_message)
        
        assert "time-sensitive" in tags
    
    @pytest.mark.asyncio
    async def test_process_batch_skip_processed(self, processor, sample_message):
        """Test that already processed messages are skipped."""
        # Mark message as already processed
        sample_message.processed = True
        
        batch = MessageBatch(
            messages=[sample_message],
            batch_id="test_batch",
            platform=MessagePlatform.SMS,
            timestamp=datetime.now(),
            total_count=1
        )
        
        results = await processor.process_batch(batch)
        
        # Should return empty results since message was already processed
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_error_handling(self, processor):
        """Test error handling in batch processing."""
        # Create a message with invalid data to trigger an error
        invalid_message = UnifiedMessage(
            id="invalid",
            platform=MessagePlatform.SMS,
            content="Test",
            message_type=MessageType.TEXT,
            timestamp=datetime.now(),
            author=MessageAuthor(id="test", name="test"),
            metadata=MessageMetadata(platform=MessagePlatform.SMS, message_id="test")
        )
        
        # Mock an error in priority classification by patching the method
        from unittest.mock import patch
        with patch.object(processor, '_classify_priority', side_effect=Exception("Test error")):
            batch = MessageBatch(
                messages=[invalid_message],
                batch_id="error_batch",
                platform=MessagePlatform.SMS,
                timestamp=datetime.now(),
                total_count=1
            )
            
            results = await processor.process_batch(batch)
            
            assert len(results) == 1
            result = results[0]
            assert result.success is False
            assert result.error == "Test error"
            assert result.priority_assigned == MessagePriority.MEDIUM  # Default fallback