# AstroBot - Telegram Horoscope & Tarot Bot

## Overview
AstroBot (Goroscope_bot) is a Telegram bot that provides daily horoscopes and tarot readings. Built with Python using aiogram v2 framework.

## Features
- 📝 Daily horoscope for all zodiac signs
- 🔮 Tarot card readings
- 🔔 Scheduled daily horoscope notifications
- ♻️ Change zodiac sign anytime
- User preferences stored in JSON files

## Project Structure
- `test_inline.py` - Main bot entry point with aiogram dispatcher
- `bot.py` - Storage utilities for user data
- `content.py` - Horoscope content and zodiac data
- `logic.py` - Bot logic and handlers
- `storage.py` - User data persistence
- `generator.py` - Horoscope generation
- `start_bot.sh` - Startup script that configures environment and runs the bot
- `requirements.txt` - Python dependencies

## Setup
- Language: Python 3.11
- Framework: aiogram 2.25.2 (async Telegram bot framework)
- Database: JSON file-based storage

## Environment Variables
- `BOT_TOKEN` or `TELEGRAM_BOT_TOKEN` - Telegram Bot API token (required, configured in Replit Secrets)
  - The startup script automatically maps TELEGRAM_BOT_TOKEN to BOT_TOKEN
- `TZ` - Timezone (default: Europe/Madrid)

## Replit Configuration
- Workflow: Configured to run `bash start_bot.sh`
- The workflow starts automatically when the Repl runs
- Status: Bot is running and polling for messages

## Recent Changes
- 2025-11-12: Initial GitHub import and Replit environment setup
- Installed Python 3.11 and dependencies (aiogram 2.25.2, python-dotenv)
- Fixed BOT_TOKEN environment variable mapping (TELEGRAM_BOT_TOKEN → BOT_TOKEN)
- Identified correct entry point (test_inline.py instead of bot.py)
- Workflow configured and verified running
- Bot successfully connected to Telegram and polling

## Running the Bot
The bot runs in polling mode via the configured workflow.
- Automatic: Workflow starts on Repl run
- Manual command: `bash start_bot.sh`

## Bot Information
- Bot Name: Goroscope_bot
- Telegram Handle: @Goroscope_chanel_bot
- Current Status: Running and polling for updates
