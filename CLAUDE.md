# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plan & Review

### Before starting work

- Always in plan mode to make a plan
- After get the plan, make sure you Write the plan to .claude/tasks/TASK_NAME.md.
- The plan should be a detailed implementation plan and the reasoning behind them, as well as tasks broken down.
- If the task require external knowledge or certain package, also research to get latest knowledge (Use Task tool for research)
- Don't over plan it, always think MVP.
- Once you write the plan, firstly ask me to review it. Do not continue until I approve the plan.

### While implementing

- You should update the plan as you work.
- After you complete tasks in the plan, you should update and append detailed descriptions of the changes you made, so following tasks can be easily hand over to other engineers.

## Project Overview

GhostRider is a unified messaging application manager that processes messages across multiple platforms (Slack, Gmail, Outlook, Discord, Telegram, SMS). The system generates intelligent summaries, contextual responses, and automated actions based on message priority and context.

## Architecture

- **Core Module**: `src/ghostrider/` contains the main application logic
- **Entry Point**: `src/ghostrider/main.py:main()` - currently a placeholder that prints startup message
- **Package Structure**: Standard Python package with Poetry for dependency management

## Development Commands

### Environment Setup

```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell
```

### Running the Application

```bash
# Run directly with Poetry
poetry run ghostrider

# Or run the module
poetry run python -m ghostrider.main
```

### Testing

```bash
# Run tests (when implemented)
poetry run pytest

# Run tests with coverage (when implemented)
poetry run pytest --cov=ghostrider
```

### Development Tools

```bash
# Add new dependencies
poetry add package_name

# Add development dependencies
poetry add --group dev package_name

# Install development dependencies
poetry install --with dev

# Code formatting and linting
poetry run ruff check src tests
poetry run ruff format src tests
poetry run mypy src

# Run all quality checks
poetry run ruff check src tests && poetry run ruff format --check src tests && poetry run mypy src

# Pre-commit setup (one-time)
poetry run pre-commit install

# Run pre-commit manually
poetry run pre-commit run --all-files
```

## SMS Integration with TextBee

### TextBee Setup for Google Pixel

GhostRider integrates with your Google Pixel phone via TextBee SMS gateway for real-time SMS processing.

#### Step 1: TextBee Account Setup

1. **Create Account**: Register at [textbee.dev](https://textbee.dev)
2. **Download App**: Get the Android app from [dl.textbee.dev](https://dl.textbee.dev)
3. **Install on Pixel**: Install and grant SMS permissions

#### Step 2: Device Connection

**QR Code Method (Recommended):**
1. Go to TextBee Dashboard
2. Click "Register Device"
3. Scan QR with TextBee app on your Pixel

**Manual Method:**
1. Generate API key from dashboard
2. Open TextBee app on Pixel
3. Enter API key manually

#### Step 3: GhostRider Configuration

Create a `.env` file in the project root:

```bash
# TextBee SMS Configuration
TEXTBEE_API_KEY=your_api_key_here
TEXTBEE_DEVICE_ID=your_device_id_here

# Optional: SMS polling interval (seconds)
SMS__POLLING_INTERVAL=10
```

#### Step 4: Install and Run

```bash
# Install with SMS dependencies
poetry install

# Run GhostRider
poetry run ghostrider
```

### SMS Features

- **Real-time SMS Reception**: Polls TextBee API for new messages every 10 seconds
- **SMS Sending**: Send replies through your Pixel phone
- **Priority Classification**: Automatic urgency scoring for SMS messages
- **Context Analysis**: Extract tags like 'financial', 'meeting', 'security' from SMS content
- **Deduplication**: Prevents processing the same SMS multiple times

### SMS Priority Rules

- **Urgent**: Keywords like 'urgent', 'emergency', 'help', 'problem'
- **High**: Keywords like 'important', 'deadline', 'meeting', 'payment' 
- **Medium**: Default priority for regular messages
- **Low**: Keywords like 'fyi', 'newsletter', 'update'

Additional factors:
- Short SMS messages (< 50 chars) get higher urgency
- Messages outside business hours (8 AM - 6 PM) get urgency boost
- Messages with URLs, phone numbers get special context tags

### Troubleshooting SMS

**Connection Issues:**
- Verify API key and device ID in `.env` file
- Check TextBee app has SMS permissions on Pixel
- Ensure Pixel has internet connection

**Missing Messages:**
- Check TextBee dashboard for device status
- Verify SMS permissions weren't revoked
- Restart TextBee app if needed

**Rate Limiting:**
- TextBee has rate limits for API calls
- GhostRider respects polling intervals to avoid limits
- Consider upgrading to TextBee Pro for higher limits

## Key Implementation Areas

Based on the README requirements, the system needs to implement:

1. **Message Reception Layer**: ✅ SMS (TextBee), Slack, Discord, Gmail integrations
2. **Processing Queue**: ✅ Asynchronous message processing system
3. **Intelligence Engine**: ✅ Priority classification and context analysis
4. **Response Generation**: AI-powered contextual responses (TODO)
5. **Action Automation**: Automated responses based on priority thresholds (TODO)

## Current State

The project is in early initialization phase with:

- Basic Poetry project structure
- Placeholder main entry point
- No external dependencies yet
- Extensive feature roadmap defined in README.md

The codebase is currently minimal and ready for core feature development.
