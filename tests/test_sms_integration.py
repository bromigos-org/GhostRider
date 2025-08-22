"""Tests for SMS integration with TextBee."""

from datetime import datetime
from typing import Any
from unittest.mock import Mock, patch

import pytest

from ghostrider.models import MessagePlatform, MessageType
from ghostrider.platforms.sms import TextBeeConfig, TextBeeSMSPlatform


@pytest.fixture
def textbee_config() -> TextBeeConfig:
    """Create a test TextBee configuration."""
    return TextBeeConfig(
        api_key="test_api_key",
        device_id="test_device_id",
        polling_interval=1,  # Fast polling for tests
    )


@pytest.fixture
def sms_platform(textbee_config: TextBeeConfig) -> TextBeeSMSPlatform:
    """Create a TextBee SMS platform instance."""
    return TextBeeSMSPlatform(textbee_config)


@pytest.fixture
def sample_sms_data() -> dict[str, Any]:
    """Sample SMS data from TextBee API."""
    return {
        "id": "12345",
        "message": "Hello, this is a test SMS message",
        "phone": "+1234567890",
        "timestamp": 1640995200000,  # 2022-01-01 00:00:00 UTC
        "direction": "received",
    }


class TestTextBeeSMSPlatform:
    """Test TextBee SMS platform integration."""

    def test_init(self, textbee_config: TextBeeConfig) -> None:
        """Test SMS platform initialization."""
        platform = TextBeeSMSPlatform(textbee_config)

        assert platform.platform_name == "sms"
        assert platform.config == textbee_config
        assert platform.session.headers["x-api-key"] == "test_api_key"
        assert platform.processed_message_ids == set()

    @pytest.mark.asyncio
    @patch("requests.Session.get")
    async def test_connect_success(self, mock_get: Mock, sms_platform: TextBeeSMSPlatform) -> None:
        """Test successful connection to TextBee API."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        await sms_platform.connect()

        mock_get.assert_called_once()
        assert "status" in mock_get.call_args[0][0]

    @pytest.mark.asyncio
    @patch("requests.Session.get")
    async def test_connect_failure(self, mock_get: Mock, sms_platform: TextBeeSMSPlatform) -> None:
        """Test failed connection to TextBee API."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_get.return_value = mock_response

        with pytest.raises(ConnectionError):
            await sms_platform.connect()

    @pytest.mark.asyncio
    @patch("requests.Session.post")
    async def test_send_message_success(self, mock_post: Mock, sms_platform: TextBeeSMSPlatform) -> None:
        """Test successful SMS sending."""
        # Mock successful send response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = await sms_platform.send_message("+1234567890", "Test message")

        assert result is True
        mock_post.assert_called_once()

        # Check request payload
        call_args = mock_post.call_args
        assert call_args[1]["json"]["recipients"] == ["+1234567890"]
        assert call_args[1]["json"]["message"] == "Test message"

    @pytest.mark.asyncio
    @patch("requests.Session.post")
    async def test_send_message_failure(self, mock_post: Mock, sms_platform: TextBeeSMSPlatform) -> None:
        """Test failed SMS sending."""
        # Mock failed send response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Send failed")
        mock_post.return_value = mock_response

        result = await sms_platform.send_message("+1234567890", "Test message")

        assert result is False

    @pytest.mark.asyncio
    @patch("requests.Session.get")
    async def test_receive_messages_success(
        self, mock_get: Mock, sms_platform: TextBeeSMSPlatform, sample_sms_data: dict[str, Any]
    ) -> None:
        """Test successful SMS receiving."""
        # Mock successful receive response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"messages": [sample_sms_data]}
        mock_get.return_value = mock_response

        messages = await sms_platform.receive_messages()

        assert len(messages) == 1

        message = messages[0]
        assert message.id == "sms_12345"
        assert message.platform == MessagePlatform.SMS
        assert message.content == "Hello, this is a test SMS message"
        assert message.message_type == MessageType.TEXT
        assert message.author.phone == "+1234567890"
        assert message.sms_metadata is not None
        assert message.sms_metadata.phone_number == "+1234567890"
        assert message.sms_metadata.device_id == "test_device_id"

    @pytest.mark.asyncio
    @patch("requests.Session.get")
    async def test_receive_messages_empty(self, mock_get: Mock, sms_platform: TextBeeSMSPlatform) -> None:
        """Test receiving when no new messages."""
        # Mock empty response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"messages": []}
        mock_get.return_value = mock_response

        messages = await sms_platform.receive_messages()

        assert len(messages) == 0

    @pytest.mark.asyncio
    @patch("requests.Session.get")
    async def test_receive_messages_deduplication(
        self, mock_get: Mock, sms_platform: TextBeeSMSPlatform, sample_sms_data: dict[str, Any]
    ) -> None:
        """Test message deduplication."""
        # Mock response with same message twice
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"messages": [sample_sms_data]}
        mock_get.return_value = mock_response

        # First call should return the message
        messages1 = await sms_platform.receive_messages()
        assert len(messages1) == 1

        # Second call should return empty (message already processed)
        messages2 = await sms_platform.receive_messages()
        assert len(messages2) == 0

    def test_convert_to_unified_message(
        self, sms_platform: TextBeeSMSPlatform, sample_sms_data: dict[str, Any]
    ) -> None:
        """Test SMS data conversion to unified message."""
        message = sms_platform._convert_to_unified_message(sample_sms_data)

        assert message.id == "sms_12345"
        assert message.platform == MessagePlatform.SMS
        assert message.content == "Hello, this is a test SMS message"
        assert message.message_type == MessageType.TEXT
        assert message.author.id == "+1234567890"
        assert message.author.name == "+1234567890"
        assert message.author.phone == "+1234567890"
        assert message.metadata.platform == MessagePlatform.SMS
        assert message.metadata.message_id == "12345"
        assert message.sms_metadata is not None
        assert message.sms_metadata.device_id == "test_device_id"
        assert message.sms_metadata.phone_number == "+1234567890"

    def test_convert_timestamp_formats(self, sms_platform: TextBeeSMSPlatform) -> None:
        """Test different timestamp format conversions."""
        # Test Unix timestamp (milliseconds)
        sms_data_unix = {"id": "1", "message": "Test", "phone": "+1234567890", "timestamp": 1640995200000}

        message = sms_platform._convert_to_unified_message(sms_data_unix)
        expected_date = datetime.fromtimestamp(1640995200)
        assert message.timestamp.replace(microsecond=0) == expected_date

        # Test ISO string timestamp
        sms_data_iso = {"id": "2", "message": "Test", "phone": "+1234567890", "timestamp": "2022-01-01T00:00:00Z"}

        message = sms_platform._convert_to_unified_message(sms_data_iso)
        assert message.timestamp.year == 2022
        assert message.timestamp.month == 1
        assert message.timestamp.day == 1
