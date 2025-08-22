"""Integration tests for GhostRider SMS functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from ghostrider.config import GhostRiderConfig, SMSConfig
from ghostrider.core import GhostRiderApp
from ghostrider.models import MessageBatch, MessagePlatform


@pytest.fixture
def sms_config():
    """Create SMS configuration for testing."""
    return SMSConfig(
        enabled=True,
        textbee_api_key="test_api_key",
        textbee_device_id="test_device_id",
        polling_interval=1
    )


@pytest.fixture
def app_config(sms_config):
    """Create GhostRider configuration for testing."""
    return GhostRiderConfig(
        sms=sms_config,
        debug=True
    )


@pytest.fixture
def ghost_rider_app(app_config):
    """Create GhostRider app instance."""
    return GhostRiderApp(app_config)


class TestGhostRiderIntegration:
    """Test GhostRider application integration."""
    
    @pytest.mark.asyncio
    @patch('ghostrider.platforms.sms.requests.Session.get')
    async def test_app_start_sms_enabled(self, mock_get, ghost_rider_app):
        """Test app startup with SMS platform enabled."""
        # Mock TextBee API connection
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        await ghost_rider_app.start()
        
        # Check SMS platform was initialized
        assert 'sms' in ghost_rider_app.platforms
        assert ghost_rider_app.running is True
        assert len(ghost_rider_app.tasks) > 0
        
        await ghost_rider_app.shutdown()
    
    @pytest.mark.asyncio
    async def test_app_start_sms_disabled(self, app_config):
        """Test app startup with SMS platform disabled."""
        # Disable SMS
        app_config.sms.enabled = False
        app = GhostRiderApp(app_config)
        
        await app.start()
        
        # Check no SMS platform was initialized
        assert 'sms' not in app.platforms
        assert app.running is True
        
        await app.shutdown()
    
    @pytest.mark.asyncio
    @patch('ghostrider.platforms.sms.requests.Session.get')
    async def test_sms_connection_failure(self, mock_get, ghost_rider_app):
        """Test handling of SMS connection failure."""
        # Mock failed API connection
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Connection failed")
        mock_get.return_value = mock_response
        
        await ghost_rider_app.start()
        
        # App should start but without SMS platform
        assert 'sms' not in ghost_rider_app.platforms
        assert ghost_rider_app.running is True
        
        await ghost_rider_app.shutdown()
    
    @pytest.mark.asyncio
    @patch('ghostrider.platforms.sms.requests.Session.get')
    async def test_message_processing_flow(self, mock_get, ghost_rider_app):
        """Test complete message processing flow."""
        # Mock TextBee API responses
        mock_status_response = Mock()
        mock_status_response.raise_for_status.return_value = None
        
        mock_messages_response = Mock()
        mock_messages_response.raise_for_status.return_value = None
        mock_messages_response.json.return_value = {
            "messages": [{
                "id": "test123",
                "message": "URGENT: Server is down! Need help ASAP!",
                "phone": "+1234567890",
                "timestamp": 1640995200000,
                "direction": "received"
            }]
        }
        
        # First call for connection, subsequent calls for messages
        mock_get.side_effect = [mock_status_response, mock_messages_response, mock_messages_response]
        
        await ghost_rider_app.start()
        
        # Simulate one polling cycle
        sms_platform = ghost_rider_app.platforms['sms']
        messages = await sms_platform.receive_messages()
        
        assert len(messages) == 1
        message = messages[0]
        assert message.content == "URGENT: Server is down! Need help ASAP!"
        assert message.platform == MessagePlatform.SMS
        
        # Process the message
        batch = MessageBatch(
            messages=messages,
            batch_id="test_batch",
            platform=MessagePlatform.SMS,
            timestamp=datetime.now(),
            total_count=1
        )
        
        await ghost_rider_app._process_message_batch(batch)
        
        # Check message was processed and classified as urgent
        assert message.processed is True
        assert message.priority.value == 'urgent'
        assert message.urgency_score >= 0.8
        
        await ghost_rider_app.shutdown()
    
    @pytest.mark.asyncio
    @patch('ghostrider.platforms.sms.requests.Session.post')
    @patch('ghostrider.platforms.sms.requests.Session.get')
    async def test_sms_sending(self, mock_get, mock_post, ghost_rider_app):
        """Test SMS sending functionality."""
        # Mock connection
        mock_status_response = Mock()
        mock_status_response.raise_for_status.return_value = None
        mock_get.return_value = mock_status_response
        
        # Mock successful send
        mock_send_response = Mock()
        mock_send_response.raise_for_status.return_value = None
        mock_send_response.json.return_value = {"success": True}
        mock_post.return_value = mock_send_response
        
        await ghost_rider_app.start()
        
        # Test sending message
        sms_platform = ghost_rider_app.platforms['sms']
        result = await sms_platform.send_message("+1234567890", "Test reply")
        
        assert result is True
        mock_post.assert_called_once()
        
        await ghost_rider_app.shutdown()
    
    @pytest.mark.asyncio
    async def test_app_shutdown_graceful(self, ghost_rider_app):
        """Test graceful application shutdown."""
        with patch('ghostrider.platforms.sms.requests.Session.get') as mock_get:
            # Mock connection
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await ghost_rider_app.start()
            
            assert ghost_rider_app.running is True
            assert len(ghost_rider_app.tasks) > 0
            
            # Shutdown
            await ghost_rider_app.shutdown()
            
            assert ghost_rider_app.running is False
    
    @pytest.mark.asyncio 
    @patch('ghostrider.platforms.sms.requests.Session.get')
    async def test_message_deduplication(self, mock_get, ghost_rider_app):
        """Test that duplicate messages are not processed twice."""
        # Mock connection and messages
        mock_status_response = Mock()
        mock_status_response.raise_for_status.return_value = None
        
        mock_messages_response = Mock()
        mock_messages_response.raise_for_status.return_value = None
        mock_messages_response.json.return_value = {
            "messages": [{
                "id": "duplicate123",
                "message": "Test duplicate message",
                "phone": "+1234567890", 
                "timestamp": 1640995200000,
                "direction": "received"
            }]
        }
        
        mock_get.side_effect = [mock_status_response, mock_messages_response, mock_messages_response]
        
        await ghost_rider_app.start()
        
        sms_platform = ghost_rider_app.platforms['sms']
        
        # First call should return message
        messages1 = await sms_platform.receive_messages()
        assert len(messages1) == 1
        
        # Second call should return empty (deduplication)
        messages2 = await sms_platform.receive_messages()
        assert len(messages2) == 0
        
        await ghost_rider_app.shutdown()