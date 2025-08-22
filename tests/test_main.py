"""Basic tests for GhostRider main module."""

import contextlib

from ghostrider.main import main


def test_main_runs() -> None:
    """Test that main function runs without error."""
    # For now, just ensure main() doesn't crash
    with contextlib.suppress(SystemExit):
        main()
