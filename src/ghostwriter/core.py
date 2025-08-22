"""Core GhostRider application."""

import asyncio
from typing import Any

from .config import GhostWriterConfig
from .models import MessageBatch
from .platforms.discord import DiscordPlatform
from .platforms.sms import TextBeeConfig, TextBeeSMSPlatform
from .processor import MessageProcessor


class GhostRiderApp:
    """Main GhostRider application."""

    def __init__(self, config: GhostWriterConfig):
        """Initialize GhostRider application."""
        self.config = config
        self.platforms: dict[str, Any] = {}
        self.processor = MessageProcessor()
        self.running = False
        self.tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start GhostRider application."""
        print("🔧 Initializing platforms...")

        # Initialize SMS platform if enabled
        if self.config.sms.enabled:
            await self._setup_sms_platform()
        else:
            print("⚠️  SMS platform disabled (missing configuration)")

        # Initialize Discord platform if enabled
        if self.config.discord.enabled:
            await self._setup_discord_platform()
        else:
            print("⚠️  Discord platform disabled (missing configuration)")

        # TODO: Initialize other platforms (Slack, Gmail)

        # Start message processing
        self.running = True

        # Start platform monitoring tasks
        for platform_name, platform in self.platforms.items():
            task = asyncio.create_task(self._monitor_platform(platform_name, platform))
            self.tasks.append(task)

        print(f"✅ Started {len(self.platforms)} platform(s)")

    async def _setup_sms_platform(self) -> None:
        """Set up TextBee SMS platform."""
        try:
            textbee_config = TextBeeConfig(
                api_key=self.config.sms.textbee_api_key,
                device_id=self.config.sms.textbee_device_id,
                polling_interval=self.config.sms.polling_interval,
            )

            sms_platform = TextBeeSMSPlatform(textbee_config)
            await sms_platform.connect()

            self.platforms["sms"] = sms_platform
            print("📱 SMS platform initialized (TextBee)")

        except Exception as e:
            print(f"❌ Failed to initialize SMS platform: {e}")

    async def _setup_discord_platform(self) -> None:
        """Set up Discord OAuth platform."""
        try:
            discord_platform = DiscordPlatform(self.config.discord)
            await discord_platform.connect()

            # Check if user needs to authenticate
            if not self.config.discord.client_id:
                print("⚠️  Discord client_id not configured. Please set DISCORD__CLIENT_ID in .env")
                return

            self.platforms["discord"] = discord_platform
            print("💬 Discord platform initialized (OAuth)")
            print("🔗 To authenticate, use the OAuth URL from the Discord service")

        except Exception as e:
            print(f"❌ Failed to initialize Discord platform: {e}")

    async def _monitor_platform(self, platform_name: str, platform: Any) -> None:
        """Monitor a platform for new messages."""
        print(f"👁️  Starting monitoring for {platform_name}")

        while self.running:
            try:
                # Get new messages
                messages = await platform.receive_messages()

                if messages:
                    print(f"📥 Received {len(messages)} new message(s) from {platform_name}")

                    # Create message batch
                    batch = MessageBatch(
                        messages=messages,
                        batch_id=f"{platform_name}_{asyncio.get_event_loop().time()}",
                        platform=messages[0].platform,
                        timestamp=messages[0].timestamp,
                        total_count=len(messages),
                    )

                    # Process messages
                    await self._process_message_batch(batch)

                # Wait before next check
                if hasattr(platform, "config") and hasattr(platform.config, "polling_interval"):
                    await asyncio.sleep(platform.config.polling_interval)
                else:
                    await asyncio.sleep(self.config.processing.processing_interval)

            except Exception as e:
                print(f"❌ Error monitoring {platform_name}: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _process_message_batch(self, batch: MessageBatch) -> None:
        """Process a batch of messages."""
        try:
            print(f"⚙️  Processing batch of {batch.total_count} messages...")

            # Process messages for priority and context
            results = await self.processor.process_batch(batch)

            # Log results
            for result in results:
                if result.success:
                    print(
                        f"✅ Processed message {result.message_id[:8]}... "
                        f"Priority: {result.priority_assigned}, "
                        f"Score: {result.urgency_score:.2f}, "
                        f"Tags: {', '.join(result.context_tags) if result.context_tags else 'none'}"
                    )
                else:
                    print(f"❌ Failed to process message {result.message_id[:8]}...: {result.error}")

            # TODO: Implement actions based on priority
            await self._handle_processed_messages(batch, results)

        except Exception as e:
            print(f"❌ Error processing message batch: {e}")

    async def _handle_processed_messages(self, batch: MessageBatch, results: Any) -> None:
        """Handle processed messages based on priority."""

        for message in batch.messages:
            if not message.processed:
                continue

            # Log high priority messages
            if message.priority.value in ["high", "urgent"]:
                print(f"🚨 HIGH PRIORITY MESSAGE from {message.platform.value}:")
                print(f"   From: {message.author.name}")
                print(f"   Content: {message.content[:100]}...")
                print(f"   Priority: {message.priority.value} (score: {message.urgency_score:.2f})")
                if message.context_tags:
                    print(f"   Tags: {', '.join(message.context_tags)}")
                print()

            # TODO: Implement automated responses
            # TODO: Implement notification routing
            # TODO: Implement message storage

    async def run_forever(self) -> None:
        """Keep the application running."""
        while self.running:
            await asyncio.sleep(1)

    async def shutdown(self) -> None:
        """Shutdown GhostRider application."""
        print("🛑 Shutting down GhostRider...")
        self.running = False

        # Cancel all running tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        # Disconnect from platforms
        for platform_name, platform in self.platforms.items():
            try:
                await platform.disconnect()
                print(f"📴 Disconnected from {platform_name}")
            except Exception as e:
                print(f"⚠️  Error disconnecting from {platform_name}: {e}")

        print("👋 GhostRider shutdown complete")
