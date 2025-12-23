#!/usr/bin/env python3
# =============================================================================
# Telegram Telethon Setup Script
# =============================================================================
"""
Interactive script for setting up Telegram authentication with Telethon.

This script handles:
1. Session creation and authentication
2. Phone number verification
3. 2FA password (if enabled)
4. Session file storage for Docker persistence

Usage (local):
    python scripts/setup_telegram_telethon.py

Usage (Docker):
    docker-compose exec osint-oa python scripts/setup_telegram_telethon.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_banner():
    """Display setup banner."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    TELEGRAM TELETHON SETUP                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  This script will authenticate your Telegram session using Telethon.     ║
║                                                                           ║
║  Requirements:                                                            ║
║  1. Telegram API credentials from https://my.telegram.org/apps           ║
║  2. Access to your Telegram account to receive verification code         ║
║  3. 2FA password if you have it enabled                                  ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)


def check_telethon():
    """Check if Telethon is installed."""
    try:
        import telethon
        print(f"✅ Telethon version: {telethon.__version__}")
        return True
    except ImportError:
        print("❌ Telethon not installed. Install with: pip install telethon")
        return False


def check_credentials():
    """Verify Telegram credentials are configured."""
    app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
    api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
    
    if not app_id or not api_hash:
        print("\n❌ ERROR: Telegram credentials not configured.")
        print("\n   Configure in your .env file:")
        print("   TG_APP_ID=your_app_id")
        print("   TG_API_HASH=your_api_hash")
        print("\n   Get credentials at: https://my.telegram.org/apps")
        return None, None
    
    try:
        app_id_int = int(app_id)
    except ValueError:
        print(f"\n❌ ERROR: TG_APP_ID must be a number, got: {app_id}")
        return None, None
    
    print(f"\n✅ Credentials found:")
    print(f"   App ID: {app_id[:4]}{'*' * (len(app_id) - 4) if len(app_id) > 4 else ''}")
    print(f"   API Hash: {api_hash[:6]}{'*' * (len(api_hash) - 6)}")
    
    return app_id_int, api_hash


def get_session_path():
    """Get the session file path."""
    session_dir = os.getenv(
        "TELEGRAM_SESSION_PATH",
        os.getenv("TG_SESSION_PATH", str(Path(__file__).parent.parent / "data" / "telegram-session"))
    )
    
    # Create directory if it doesn't exist
    os.makedirs(session_dir, exist_ok=True)
    
    session_file = os.path.join(session_dir, "osint_bot")
    print(f"\n📂 Session will be saved to: {session_file}.session")
    
    return session_file


async def run_authentication(app_id: int, api_hash: str, session_file: str):
    """Run the interactive authentication process."""
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    
    print("\n🔐 Starting authentication process...")
    print("   (Follow the prompts below)\n")
    print("-" * 60)
    
    client = TelegramClient(
        session_file,
        app_id,
        api_hash,
        system_version="OSINT-OA 1.0",
        device_model="OSINT Agent",
        app_version="1.0.0",
    )
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            print("\n✅ Session already authorized!")
            me = await client.get_me()
            print(f"   Logged in as: {me.first_name} (@{me.username or 'no username'})")
            print(f"   User ID: {me.id}")
            
            response = input("\n   Create new session anyway? (y/N): ").strip().lower()
            if response != 'y':
                await client.disconnect()
                return True
            
            # Log out and start fresh
            await client.log_out()
            await client.connect()
        
        # Start interactive login
        print("\n📱 Enter your phone number (with country code, e.g., +1234567890):")
        phone = input("   Phone: ").strip()
        
        if not phone:
            print("❌ Phone number is required")
            return False
        
        # Send code request
        print("\n📨 Sending verification code...")
        await client.send_code_request(phone)
        
        print("✅ Code sent! Check your Telegram app.")
        print("\n🔢 Enter the verification code you received:")
        code = input("   Code: ").strip()
        
        if not code:
            print("❌ Verification code is required")
            return False
        
        try:
            # Try to sign in with the code
            await client.sign_in(phone, code)
            
        except SessionPasswordNeededError:
            # 2FA is enabled
            print("\n🔐 Two-factor authentication is enabled.")
            print("   Enter your 2FA password:")
            
            import getpass
            password = getpass.getpass("   Password: ")
            
            await client.sign_in(password=password)
        
        # Check if successful
        if await client.is_user_authorized():
            me = await client.get_me()
            print("\n" + "=" * 60)
            print("✅ AUTHENTICATION SUCCESSFUL!")
            print("=" * 60)
            print(f"   Logged in as: {me.first_name} (@{me.username or 'no username'})")
            print(f"   User ID: {me.id}")
            print(f"   Session saved to: {session_file}.session")
            print("\n   You can now start the OSINT bot!")
            print("=" * 60)
            
            await client.disconnect()
            return True
        else:
            print("\n❌ Authentication failed. Please try again.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        return False
    finally:
        if client.is_connected():
            await client.disconnect()


async def test_connection(app_id: int, api_hash: str, session_file: str):
    """Test the connection with existing session."""
    from telethon import TelegramClient
    
    print("\n🔄 Testing connection...")
    
    client = TelegramClient(session_file, app_id, api_hash)
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Connection successful!")
            print(f"   Logged in as: {me.first_name} (@{me.username or 'no username'})")
            
            # Try to list dialogs
            print("\n📋 Recent dialogs:")
            count = 0
            async for dialog in client.iter_dialogs(limit=5):
                print(f"   • {dialog.name} (ID: {dialog.id})")
                count += 1
            
            if count == 0:
                print("   (No dialogs found)")
            
            return True
        else:
            print("❌ Session not authorized. Run setup first.")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    finally:
        await client.disconnect()


def main():
    """Main entry point."""
    print_banner()
    
    # Check Telethon installation
    if not check_telethon():
        sys.exit(1)
    
    # Check credentials
    app_id, api_hash = check_credentials()
    if not app_id or not api_hash:
        sys.exit(1)
    
    # Get session path
    session_file = get_session_path()
    
    # Check if session exists
    session_exists = os.path.exists(f"{session_file}.session")
    
    print("\n" + "=" * 60)
    print("What would you like to do?")
    print("=" * 60)
    print("  1. New authentication (create/replace session)")
    if session_exists:
        print("  2. Test existing session")
    print("  q. Quit")
    print()
    
    choice = input("Select option: ").strip().lower()
    
    if choice == '1':
        asyncio.run(run_authentication(app_id, api_hash, session_file))
    elif choice == '2' and session_exists:
        asyncio.run(test_connection(app_id, api_hash, session_file))
    elif choice == 'q':
        print("\nGoodbye!")
    else:
        print("Invalid option.")
    
    print()


if __name__ == "__main__":
    main()
