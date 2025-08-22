#!/usr/bin/env python3
"""Test script for Discord OAuth integration."""

import asyncio
from pathlib import Path

from src.ghostwriter.config import load_config
from src.ghostwriter.models import UnifiedMessage
from src.ghostwriter.platforms.discord import DiscordPlatform


async def test_discord_oauth() -> None:
    """Test Discord OAuth flow."""
    print("🧪 Testing Discord OAuth Integration")
    print("=" * 50)

    # Load configuration
    config = load_config()

    if not config.discord.enabled:
        print("❌ Discord not enabled in configuration")
        print("Please set DISCORD__ENABLED=true in your .env file")
        return

    if not config.discord.client_id or not config.discord.client_secret:
        print("❌ Discord OAuth credentials missing")
        print("Please set DISCORD__CLIENT_ID and DISCORD__CLIENT_SECRET in your .env file")
        return

    # Initialize Discord platform
    discord = DiscordPlatform(config.discord)
    await discord.connect()

    try:
        # Generate OAuth URL
        oauth_url = discord.get_oauth_url()
        print(f"🔗 OAuth URL: {oauth_url}")
        print()
        print("Steps to test:")
        print("1. Copy the OAuth URL above")
        print("2. Open it in your browser")
        print("3. Authorize GhostRider to access your Discord")
        print("4. Copy the authorization code from the redirect URL")
        print("5. Enter it below")
        print()

        # Get authorization code from user
        auth_code = input("Enter authorization code: ").strip()

        if not auth_code:
            print("❌ No authorization code provided")
            return

        # Exchange code for token
        print("🔄 Exchanging code for token...")
        user_id = await discord.authenticate_user(auth_code)
        print(f"✅ Successfully authenticated user: {user_id}")

        # Test fetching user channels
        print("🔄 Fetching user channels...")
        channels = await discord.get_user_channels(user_id)
        print(f"✅ Found {len(channels)} channels/DMs")

        for i, channel in enumerate(channels[:5]):  # Show first 5
            print(f"  {i+1}. Channel ID: {channel.channel_id}, Type: {channel.channel_type}")

        # Test fetching messages from first channel
        if channels:
            first_channel = channels[0]
            print(f"🔄 Fetching messages from channel {first_channel.channel_id}...")
            messages = await discord.fetch_channel_messages(first_channel.channel_id, user_id, limit=5)
            print(f"✅ Fetched {len(messages)} messages")

            for i, msg in enumerate(messages):
                print(f"  {i+1}. {msg.author_name}: {msg.content[:50]}...")

        # Test unified message conversion
        print("🔄 Testing unified message conversion...")
        unified_messages: list[UnifiedMessage] = await discord.receive_messages()
        print(f"✅ Converted {len(unified_messages)} messages to unified format")

        print("\n🎉 Discord integration test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await discord.disconnect()


if __name__ == "__main__":
    # Ensure we're in the right directory
    if not Path("src/ghostwriter").exists():
        print("❌ Please run this script from the GhostWriter project root directory")
        exit(1)

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Run test
    asyncio.run(test_discord_oauth())
