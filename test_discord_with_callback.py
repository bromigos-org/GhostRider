#!/usr/bin/env python3
"""Test script for Discord OAuth integration with callback server."""

import asyncio
import os
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from aiohttp import web
from aiohttp.web import Application, Request, Response

from src.ghostwriter.config import load_config
from src.ghostwriter.platforms.discord import DiscordPlatform


class OAuthCallbackServer:
    """Simple HTTP server to handle OAuth callbacks."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.auth_code: str | None = None
        self.server_task: asyncio.Task | None = None
        self.app = Application()
        self.app.router.add_get("/callback", self.handle_callback)

    async def handle_callback(self, request: Request) -> Response:
        """Handle OAuth callback and extract authorization code."""
        query_params = dict(request.query)
        
        if "code" in query_params:
            self.auth_code = query_params["code"]
            print(f"✅ Received authorization code: {self.auth_code[:20]}...")
            return Response(
                text="<h1>✅ Authorization Success!</h1>"
                     "<p>You can close this window and return to the terminal.</p>",
                content_type="text/html"
            )
        elif "error" in query_params:
            error = query_params.get("error", "unknown")
            error_description = query_params.get("error_description", "No description")
            print(f"❌ OAuth error: {error} - {error_description}")
            return Response(
                text=f"<h1>❌ Authorization Error</h1>"
                     f"<p>Error: {error}</p>"
                     f"<p>Description: {error_description}</p>",
                content_type="text/html"
            )
        else:
            return Response(
                text="<h1>❓ Invalid callback</h1>"
                     "<p>No authorization code or error received.</p>",
                content_type="text/html"
            )

    async def start(self):
        """Start the callback server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"🌐 Callback server started at http://{self.host}:{self.port}")

    async def wait_for_callback(self, timeout: int = 120) -> str | None:
        """Wait for OAuth callback with timeout."""
        start_time = time.time()
        while self.auth_code is None and (time.time() - start_time) < timeout:
            await asyncio.sleep(1)
        return self.auth_code


async def test_discord_oauth_with_callback():
    """Test Discord OAuth flow with automatic callback handling."""
    print("🧪 Testing Discord OAuth Integration with Callback Server")
    print("=" * 60)

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

    # Initialize callback server
    callback_server = OAuthCallbackServer()
    await callback_server.start()

    # Initialize Discord platform
    discord = DiscordPlatform(config.discord)
    await discord.connect()

    try:
        # Generate OAuth URL using the platform's method with correct scopes
        oauth_url = discord.generate_oauth_url()
        
        print(f"🔗 Opening OAuth URL in browser...")
        print(f"URL: {oauth_url}")
        print()
        print("Steps:")
        print("1. Browser should open automatically")
        print("2. Authorize GhostRider to access your Discord")
        print("3. You'll be redirected to the callback server")
        print("4. The test will continue automatically")
        print()

        # Open browser automatically
        webbrowser.open(oauth_url)

        # Wait for callback
        print("⏳ Waiting for authorization (up to 2 minutes)...")
        auth_code = await callback_server.wait_for_callback(timeout=120)
        
        if not auth_code:
            print("❌ No authorization code received within timeout")
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
            channel_type_name = {
                1: "DM",
                3: "Group DM",
                0: "Text Channel",
                2: "Voice Channel"
            }.get(channel.channel_type, f"Type {channel.channel_type}")
            
            print(f"  {i+1}. Channel ID: {channel.channel_id}, Type: {channel_type_name}")
            if channel.recipient_ids:
                print(f"      Recipients: {len(channel.recipient_ids)} users")

        # Test fetching messages from first channel
        if channels:
            first_channel = channels[0]
            print(f"🔄 Fetching messages from channel {first_channel.channel_id}...")
            messages = await discord.fetch_channel_messages(
                first_channel.channel_id, 
                user_id, 
                limit=5
            )
            print(f"✅ Fetched {len(messages)} messages")

            for i, msg in enumerate(messages):
                content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                print(f"  {i+1}. {msg.author_name}: {content_preview}")

        # Test unified message conversion
        print("🔄 Testing unified message conversion...")
        unified_messages = await discord.receive_messages()
        print(f"✅ Converted {len(unified_messages)} messages to unified format")

        for i, msg in enumerate(unified_messages[:3]):  # Show first 3
            print(f"  {i+1}. [{msg.platform.value}] {msg.author.name}: {msg.content[:40]}...")

        print("\n🎉 Discord integration test completed successfully!")
        print(f"📊 Summary: {len(channels)} channels, {len(unified_messages)} messages processed")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await discord.disconnect()
        print("🔌 Disconnected from Discord platform")


if __name__ == "__main__":
    # Ensure we're in the right directory
    if not Path("src/ghostwriter").exists():
        print("❌ Please run this script from the GhostWriter project root directory")
        exit(1)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    asyncio.run(test_discord_oauth_with_callback())