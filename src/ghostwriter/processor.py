"""Message processing and priority classification system."""

import re
from datetime import datetime

from .models import (
    MessageBatch,
    MessagePriority,
    MessageProcessingResult,
    UnifiedMessage,
)


class MessageProcessor:
    """Process and classify messages for priority and context."""

    def __init__(self) -> None:
        """Initialize the message processor."""
        self.urgent_keywords = [
            "urgent",
            "asap",
            "emergency",
            "critical",
            "immediate",
            "help",
            "problem",
            "issue",
            "error",
            "failure",
            "down",
        ]

        self.high_priority_keywords = [
            "important",
            "priority",
            "deadline",
            "meeting",
            "call",
            "interview",
            "review",
            "approval",
            "payment",
            "invoice",
        ]

        self.low_priority_keywords = [
            "fyi",
            "heads up",
            "update",
            "newsletter",
            "notification",
            "reminder",
            "weekly",
            "monthly",
            "digest",
        ]

    async def process_batch(self, batch: MessageBatch) -> list[MessageProcessingResult]:
        """Process a batch of messages."""
        results = []

        for message in batch.messages:
            if message.processed:
                continue

            start_time = datetime.now()

            try:
                # Classify priority
                priority, urgency_score = self._classify_priority(message)

                # Extract context tags
                context_tags = self._extract_context_tags(message)

                # Mark as processed
                message.priority = priority
                message.urgency_score = urgency_score
                message.context_tags = context_tags
                message.processed = True
                message.processing_timestamp = datetime.now()

                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds() * 1000

                result = MessageProcessingResult(
                    message_id=message.id,
                    success=True,
                    priority_assigned=priority,
                    urgency_score=urgency_score,
                    context_tags=context_tags,
                    processing_time_ms=processing_time,
                )

            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                result = MessageProcessingResult(
                    message_id=message.id,
                    success=False,
                    priority_assigned=MessagePriority.MEDIUM,
                    urgency_score=0.5,
                    context_tags=[],
                    processing_time_ms=processing_time,
                    error=str(e),
                )

            results.append(result)

        return results

    def _classify_priority(self, message: UnifiedMessage) -> tuple[MessagePriority, float]:
        """Classify message priority and calculate urgency score."""
        content = message.content.lower()
        urgency_score = 0.5  # Default medium priority

        # Check for urgent keywords
        urgent_count = sum(1 for keyword in self.urgent_keywords if keyword in content)
        if urgent_count > 0:
            urgency_score = min(1.0, 0.8 + (urgent_count * 0.1))
            return MessagePriority.URGENT, urgency_score

        # Check for high priority keywords
        high_count = sum(1 for keyword in self.high_priority_keywords if keyword in content)
        if high_count > 0:
            urgency_score = min(0.8, 0.6 + (high_count * 0.1))
            return MessagePriority.HIGH, urgency_score

        # Check for low priority keywords
        low_count = sum(1 for keyword in self.low_priority_keywords if keyword in content)
        if low_count > 0:
            urgency_score = max(0.1, 0.3 - (low_count * 0.1))
            return MessagePriority.LOW, urgency_score

        # SMS-specific rules
        # Handle both enum and string platform values
        platform_value = message.platform.value if hasattr(message.platform, "value") else str(message.platform)
        if platform_value == "sms":
            # Short SMS messages often more urgent
            if len(message.content) < 50:
                urgency_score += 0.1

            # SMS from unknown numbers might be less urgent
            if message.sms_metadata and message.sms_metadata.phone_number:
                phone = message.sms_metadata.phone_number
                if not self._is_known_contact(phone):
                    urgency_score -= 0.1

        # Time-based urgency (messages outside business hours might be more urgent)
        hour = message.timestamp.hour
        if hour < 8 or hour > 18:  # Outside 8 AM - 6 PM
            urgency_score += 0.1

        urgency_score = max(0.0, min(1.0, urgency_score))

        if urgency_score >= 0.8:
            return MessagePriority.URGENT, urgency_score
        elif urgency_score >= 0.6:
            return MessagePriority.HIGH, urgency_score
        elif urgency_score <= 0.3:
            return MessagePriority.LOW, urgency_score
        else:
            return MessagePriority.MEDIUM, urgency_score

    def _extract_context_tags(self, message: UnifiedMessage) -> list[str]:
        """Extract context tags from message content."""
        content = message.content.lower()
        tags = []

        # Platform tag - handle both enum and string platform values
        platform_value = message.platform.value if hasattr(message.platform, "value") else str(message.platform)
        tags.append(f"platform:{platform_value}")

        # Content analysis tags
        if any(word in content for word in ["meeting", "call", "zoom", "teams"]):
            tags.append("meeting")

        if any(word in content for word in ["payment", "invoice", "bill", "charge"]):
            tags.append("financial")

        if any(word in content for word in ["password", "login", "security", "account"]):
            tags.append("security")

        if any(word in content for word in ["delivery", "package", "shipped", "tracking"]):
            tags.append("delivery")

        # URL detection
        if re.search(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", content):
            tags.append("contains-link")

        # Phone number detection
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", content):
            tags.append("contains-phone")

        # Time sensitivity
        if any(word in content for word in ["today", "tomorrow", "asap", "urgent"]):
            tags.append("time-sensitive")

        return tags

    def _is_known_contact(self, phone: str) -> bool:
        """Check if phone number is from a known contact."""
        # TODO: Implement contact database lookup
        # For now, assume all contacts are unknown
        return False
