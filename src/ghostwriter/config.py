"""Configuration management for GhostWriter."""

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
    # OAuth 2.0 configuration
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    # Database configuration
    db_path: str = "ghostwriter.db"
    encryption_key: str | None = None
    # API configuration
    api_base_url: str = "https://discord.com/api/v10"
    max_messages_per_channel: int = 100


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


class GhostWriterConfig(BaseModel):
    """Main GhostWriter configuration."""

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


def load_config() -> GhostWriterConfig:
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
        client_id=os.getenv("DISCORD__CLIENT_ID"),
        client_secret=os.getenv("DISCORD__CLIENT_SECRET"),
        redirect_uri=os.getenv("DISCORD__REDIRECT_URI", "http://localhost:8080/callback"),
        db_path=os.getenv("DISCORD__DB_PATH", "ghostwriter.db"),
        encryption_key=os.getenv("DISCORD__ENCRYPTION_KEY"),
        api_base_url=os.getenv("DISCORD__API_BASE_URL", "https://discord.com/api/v10"),
        max_messages_per_channel=int(os.getenv("DISCORD__MAX_MESSAGES_PER_CHANNEL", "100")),
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
    config = GhostWriterConfig(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        sms=sms_config,
        slack=slack_config,
        discord=discord_config,
        gmail=gmail_config,
        processing=processing_config,
    )
    return config
