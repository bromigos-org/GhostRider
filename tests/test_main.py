"""Basic tests for GhostRider main module."""

from ghostrider.main import main


def test_main_runs():
    """Test that main function runs without error."""
    # For now, just ensure main() doesn't crash
    try:
        main()
    except SystemExit:
        pass  # main() might call sys.exit()