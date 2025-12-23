# Telegram Integration Setup Guide

## Overview

OSINT OA uses **Telethon** (Python native library) for direct Telegram API integration. This provides:
- Robust message delivery
- No external binary dependencies
- Full async support
- Rich HTML formatting

## Prerequisites

1. **Telegram API Credentials** from https://my.telegram.org/apps
2. **Access to your Telegram account** for initial authentication

## Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Telegram API Credentials (REQUIRED)
TG_APP_ID=your_app_id
TG_API_HASH=your_api_hash

# Target dialog for reports (REQUIRED for publishing)
TELEGRAM_TARGET_DIALOG=cht[123456]  # or @channel_username

# Optional: Bot token for webhook-style notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Session file path (optional, defaults shown)
TELEGRAM_SESSION_PATH=/app/data/telegram-session
```

### 2. Initial Authentication

**First-time setup requires interactive authentication:**

```bash
# Inside Docker container:
docker-compose exec osint-oa python scripts/setup_telegram.py

# Or locally:
python scripts/setup_telegram.py
```

The script will:
1. Ask for your phone number (with country code: +1234567890)
2. Send a verification code to your Telegram
3. Request 2FA password if enabled
4. Store the session file for future use

### 3. Verify Connection

After authentication, verify the connection:

```bash
# Via API endpoint:
curl http://localhost:5000/api/telegram/status | jq .

# Expected output when configured:
{
  "configured": true,
  "session_exists": true,
  "connected": true,
  "authorized": true,
  "user": {
    "id": 123456789,
    "username": "your_username",
    "first_name": "Your Name"
  }
}
```

### 4. Test Message

Send a test message to verify everything works:

```bash
curl -X POST http://localhost:5000/api/telegram/test \
  -H "Content-Type: application/json" \
  -d '{"message": "🔧 Test from OSINT-OA"}'
```

## Running Tests

```bash
# Run Telegram connectivity tests
docker-compose exec osint-oa python -m pytest tests/test_telegram.py -v

# Or run quick check script
docker-compose exec osint-oa python tests/test_telegram.py
```

## Dialog Identification

Telegram dialogs can be identified in several ways:

| Format | Example | Description |
|--------|---------|-------------|
| `cht[ID]` | `cht[123456789]` | Group by numeric ID |
| `@username` | `@my_channel` | Public channel/user by username |
| `dialog_name` | `OSINT Reports` | Dialog by display name |

To find dialog IDs:

```bash
curl http://localhost:5000/api/telegram/dialogs | jq .
```

## Docker Session Persistence

The session file is stored in `.telegram-session/` directory and mounted into the container:

```yaml
volumes:
  - ./.telegram-session:/app/data/telegram-session
```

**Important:** The directory must be writable by the container user (UID 999):

```bash
sudo chown -R 999:999 .telegram-session/
```

## Troubleshooting

### "Session not authorized"

Run the setup script to authenticate:
```bash
docker-compose exec osint-oa python scripts/setup_telegram.py
```

### "Unable to open database file"

Permission issue on the session directory:
```bash
sudo chown -R 999:999 .telegram-session/
```

### "Could not resolve chat"

The dialog name/ID might be incorrect. List available dialogs:
```bash
curl http://localhost:5000/api/telegram/dialogs | jq .
```

### Connection timeout

Check if the container can reach Telegram's servers:
```bash
docker-compose exec osint-oa curl -v https://api.telegram.org
```

## Security Notes

1. **Session file** contains your Telegram authentication - keep it secure
2. **Never commit** `.telegram-session/` or session files to git
3. Use **environment variables** for credentials, not hardcoded values
4. Consider using a **dedicated Telegram account** for OSINT operations

## Migration from MCP

If you were using the previous telegram-mcp binary:

1. The old `session.json` format is incompatible with Telethon
2. Run `python scripts/setup_telegram.py` to create a new session
3. Update any references from `mcp_client` to `telethon_client`
4. The API remains similar - `send_message()`, `get_dialogs()`, etc.
