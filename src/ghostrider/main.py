"""GhostRider main application."""

import asyncio
import signal
import sys
from typing import Optional

from .config import load_config
from .core import GhostRiderApp


def handle_shutdown(app: GhostRiderApp) -> None:
    """Handle shutdown signals."""
    
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}. Shutting down GhostRider...")
        asyncio.create_task(app.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def async_main() -> None:
    """Async main function."""
    
    print("🤖 Starting GhostRider...")
    
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Initialize GhostRider app
    app = GhostRiderApp(config)
    
    # Set up shutdown handling
    handle_shutdown(app)
    
    try:
        # Start the application
        await app.start()
        
        print("✅ GhostRider is running. Press Ctrl+C to stop.")
        
        # Keep the application running
        await app.run_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down GhostRider...")
    except Exception as e:
        print(f"❌ Error running GhostRider: {e}")
        sys.exit(1)
    finally:
        await app.shutdown()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n👋 GhostRider stopped.")


if __name__ == "__main__":
    main()