# =============================================================================
# Telegram Connectivity Tests
# =============================================================================
"""
Tests for Telegram integration using Telethon.

These tests verify:
1. Telethon library is properly installed
2. Configuration is correct
3. Session file accessibility
4. Client connectivity (when authenticated)

Run with: pytest tests/test_telegram.py -v
Environment: Requires TG_APP_ID and TG_API_HASH environment variables
"""

import pytest
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTelethonImport:
    """Test Telethon library availability."""
    
    def test_telethon_installed(self):
        """Test that Telethon library is installed."""
        try:
            import telethon
            assert telethon is not None
        except ImportError:
            pytest.fail("Telethon library not installed. Run: pip install telethon")
    
    def test_telethon_version(self):
        """Test Telethon version is compatible."""
        import telethon
        version = telethon.__version__
        major, minor = map(int, version.split('.')[:2])
        # Require Telethon >= 1.36
        assert major >= 1 and minor >= 36, f"Telethon version {version} is too old, need >= 1.36"


class TestTelethonClientImport:
    """Test TelethonClient module loading."""
    
    def test_client_import(self):
        """Test that TelethonClient can be imported."""
        from integrations.telegram.telethon_client import TelethonClient
        assert TelethonClient is not None
    
    def test_config_import(self):
        """Test that TelethonConfig can be imported."""
        from integrations.telegram.telethon_client import TelethonConfig
        assert TelethonConfig is not None
    
    def test_formatter_import(self):
        """Test that TelegramFormatter can be imported."""
        from integrations.telegram.telethon_client import TelegramFormatter
        assert TelegramFormatter is not None


class TestTelegramConfiguration:
    """Test Telegram configuration."""
    
    def test_env_vars_present(self):
        """Test that required environment variables are present."""
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
        
        if not app_id or not api_hash:
            pytest.skip("Telegram credentials not configured (TG_APP_ID, TG_API_HASH)")
        
        assert app_id is not None, "TG_APP_ID environment variable not set"
        assert api_hash is not None, "TG_API_HASH environment variable not set"
    
    def test_app_id_is_numeric(self):
        """Test that TG_APP_ID is a valid number."""
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        
        if not app_id:
            pytest.skip("TG_APP_ID not configured")
        
        try:
            int(app_id)
        except ValueError:
            pytest.fail(f"TG_APP_ID must be a number, got: {app_id}")
    
    def test_config_from_env(self):
        """Test TelethonConfig.from_env() works."""
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
        
        if not app_id or not api_hash:
            pytest.skip("Telegram credentials not configured")
        
        from integrations.telegram.telethon_client import TelethonConfig
        config = TelethonConfig.from_env()
        
        assert config.api_id > 0
        assert len(config.api_hash) > 0
        assert config.is_valid


class TestSessionDirectory:
    """Test session file/directory access."""
    
    def test_session_path_configured(self):
        """Test session path is configured."""
        from integrations.telegram.telethon_client import TelethonConfig
        
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
        
        if not app_id or not api_hash:
            pytest.skip("Telegram credentials not configured")
        
        config = TelethonConfig.from_env()
        session_dir = Path(config.session_path)
        
        assert session_dir.exists(), f"Session directory does not exist: {session_dir}"
        assert session_dir.is_dir(), f"Session path is not a directory: {session_dir}"
    
    def test_session_directory_writable(self):
        """Test session directory is writable."""
        session_path = os.getenv(
            "TELEGRAM_SESSION_PATH",
            os.getenv("TG_SESSION_PATH", "data/telegram-session")
        )
        
        session_dir = Path(session_path)
        if not session_dir.exists():
            session_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = session_dir / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            pytest.fail(f"Session directory is not writable: {session_dir}")


class TestTelethonClientCreation:
    """Test TelethonClient instantiation."""
    
    def test_client_creation(self):
        """Test TelethonClient can be created."""
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
        
        if not app_id or not api_hash:
            pytest.skip("Telegram credentials not configured")
        
        from integrations.telegram.telethon_client import TelethonClient
        client = TelethonClient()
        
        assert client is not None
        assert client.is_configured
    
    def test_client_formatter(self):
        """Test TelegramFormatter works correctly."""
        from integrations.telegram.telethon_client import TelegramFormatter
        
        # Test HTML escaping
        escaped = TelegramFormatter.escape_html("<script>alert('xss')</script>")
        assert "<" not in escaped
        assert "&lt;" in escaped
        
        # Test report formatting
        report = TelegramFormatter.format_osint_report(
            report="Test report content",
            query="test@example.com",
            run_id=123,
        )
        assert "OSINT" in report
        assert "test@example.com" in report


@pytest.mark.asyncio
class TestTelethonConnectivity:
    """Test actual Telegram connectivity (requires authenticated session)."""
    
    async def test_client_connect(self):
        """Test client can connect to Telegram."""
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
        
        if not app_id or not api_hash:
            pytest.skip("Telegram credentials not configured")
        
        from integrations.telegram.telethon_client import TelethonClient
        client = TelethonClient()
        
        try:
            connected = await client.connect()
            if not connected:
                pytest.skip("Session not authorized - run setup_telegram.py first")
            
            assert client.is_connected
        finally:
            await client.disconnect()
    
    async def test_get_me(self):
        """Test can retrieve authenticated user info."""
        app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
        api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
        
        if not app_id or not api_hash:
            pytest.skip("Telegram credentials not configured")
        
        from integrations.telegram.telethon_client import TelethonClient
        client = TelethonClient()
        
        try:
            connected = await client.connect()
            if not connected:
                pytest.skip("Session not authorized")
            
            me = await client._client.get_me()
            assert me is not None
            assert me.id > 0
        finally:
            await client.disconnect()


# =============================================================================
# CLI Test Runner
# =============================================================================

def run_quick_check():
    """Quick connectivity check without pytest."""
    import asyncio
    
    print("\n" + "=" * 60)
    print("TELEGRAM CONNECTIVITY CHECK")
    print("=" * 60)
    
    # Check Telethon
    print("\n1. Checking Telethon installation...")
    try:
        import telethon
        print(f"   ✅ Telethon {telethon.__version__} installed")
    except ImportError:
        print("   ❌ Telethon not installed")
        return False
    
    # Check credentials
    print("\n2. Checking credentials...")
    app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
    api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
    
    if not app_id or not api_hash:
        print("   ❌ Credentials not configured")
        print("   Set TG_APP_ID and TG_API_HASH environment variables")
        return False
    print("   ✅ Credentials found")
    
    # Check session directory
    print("\n3. Checking session directory...")
    session_path = os.getenv(
        "TELEGRAM_SESSION_PATH",
        os.getenv("TG_SESSION_PATH", "data/telegram-session")
    )
    session_dir = Path(session_path)
    
    if not session_dir.exists():
        session_dir.mkdir(parents=True, exist_ok=True)
        print(f"   📁 Created session directory: {session_dir}")
    else:
        print(f"   ✅ Session directory exists: {session_dir}")
    
    # Check for session file
    session_file = session_dir / "osint_bot.session"
    if session_file.exists():
        print(f"   ✅ Session file found: {session_file}")
    else:
        print(f"   ⚠️  No session file found - need to run setup_telegram.py")
    
    # Test connectivity
    print("\n4. Testing Telegram connectivity...")
    
    async def check_connection():
        from integrations.telegram.telethon_client import TelethonClient
        client = TelethonClient()
        
        try:
            connected = await client.connect()
            if connected:
                me = await client._client.get_me()
                print(f"   ✅ Connected as: {me.first_name} (@{me.username or 'no username'})")
                print(f"   ✅ User ID: {me.id}")
                await client.disconnect()
                return True
            else:
                print("   ❌ Not connected - session not authorized")
                print("   Run: python scripts/setup_telegram.py")
                return False
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return False
    
    result = asyncio.run(check_connection())
    
    print("\n" + "=" * 60)
    if result:
        print("✅ ALL CHECKS PASSED - Telegram is ready!")
    else:
        print("❌ SOME CHECKS FAILED - See details above")
    print("=" * 60 + "\n")
    
    return result


if __name__ == "__main__":
    # Allow running as standalone script
    run_quick_check()
