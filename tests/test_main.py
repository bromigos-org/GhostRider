"""Basic tests for GhostRider main module."""


def test_import_works() -> None:
    """Test that main module imports successfully."""
    from ghostrider.main import main

    assert main is not None


def test_models_import() -> None:
    """Test that models import successfully."""
    from ghostrider.models import MessagePriority, UnifiedMessage

    assert UnifiedMessage is not None
    assert MessagePriority is not None


def test_processor_import() -> None:
    """Test that processor imports successfully."""
    from ghostrider.processor import MessageProcessor

    processor = MessageProcessor()
    assert processor is not None
