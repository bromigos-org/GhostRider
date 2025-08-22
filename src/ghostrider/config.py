"""Configuration management for GhostRider."""

import os

from pydantic import BaseModel


class SMSConfig(BaseModel):
    """SMS platform configuration."""

    enabled: bool = True
    textbee_api_key: str
    textbee_device_id: str
    polling_interval: int = 10  # seconds


class SlackConfig(BaseModel):
    """Slack platform configuration."""

    enabled: bool = False
    bot_token: str | None = None
    app_token: str | None = None


class DiscordConfig(BaseModel):
    """Discord platform configuration."""

    enabled: bool = False
    bot_token: str | None = None
    guild_id: str | None = None


class GmailConfig(BaseModel):
    """Gmail platform configuration."""

    enabled: bool = False
    credentials_path: str | None = None
    token_path: str | None = None


class ProcessingConfig(BaseModel):
    """Message processing configuration."""

    batch_size: int = 10
    processing_interval: int = 5  # seconds
    max_retries: int = 3


class GhostRiderConfig(BaseModel):
    """Main GhostRider configuration."""

    # General settings
    debug: bool = False
    log_level: str = "INFO"

    # Platform configurations
    sms: SMSConfig
    slack: SlackConfig = SlackConfig()
    discord: DiscordConfig = DiscordConfig()
    gmail: GmailConfig = GmailConfig()

    # Processing settings
    processing: ProcessingConfig = ProcessingConfig()


def load_config() -> GhostRiderConfig:
    """Load configuration from environment and .env file."""

    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv

    load_dotenv()

    # Load SMS configuration from environment with proper nesting
    sms_config = SMSConfig(
        enabled=os.getenv("SMS__ENABLED", "true").lower() == "true",
        textbee_api_key=os.getenv("TEXTBEE_API_KEY", ""),
        textbee_device_id=os.getenv("TEXTBEE_DEVICE_ID", ""),
        polling_interval=int(os.getenv("SMS__POLLING_INTERVAL", "10")),
    )

    if not sms_config.textbee_api_key or not sms_config.textbee_device_id:
        print("Warning: TextBee SMS configuration missing. SMS platform will be disabled.")
        sms_config.enabled = False

    # Load Slack configuration
    slack_config = SlackConfig(
        enabled=os.getenv("SLACK__ENABLED", "false").lower() == "true",
        bot_token=os.getenv("SLACK__BOT_TOKEN"),
        app_token=os.getenv("SLACK__APP_TOKEN"),
    )

    # Load Discord configuration
    discord_config = DiscordConfig(
        enabled=os.getenv("DISCORD__ENABLED", "false").lower() == "true",
        bot_token=os.getenv("DISCORD__BOT_TOKEN"),
        guild_id=os.getenv("DISCORD__GUILD_ID"),
    )

    # Load Gmail configuration
    gmail_config = GmailConfig(
        enabled=os.getenv("GMAIL__ENABLED", "false").lower() == "true",
        credentials_path=os.getenv("GMAIL__CREDENTIALS_PATH"),
        token_path=os.getenv("GMAIL__TOKEN_PATH"),
    )

    # Load Processing configuration
    processing_config = ProcessingConfig(
        batch_size=int(os.getenv("PROCESSING__BATCH_SIZE", "10")),
        processing_interval=int(os.getenv("PROCESSING__PROCESSING_INTERVAL", "5")),
        max_retries=int(os.getenv("PROCESSING__MAX_RETRIES", "3")),
    )

    # Create main configuration manually to avoid BaseSettings auto-loading conflicts
    config = GhostRiderConfig(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        sms=sms_config,
        slack=slack_config,
        discord=discord_config,
        gmail=gmail_config,
        processing=processing_config,
    )
    return config
