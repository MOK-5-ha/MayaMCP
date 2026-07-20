"""Unit tests for CryptoPaymentClient.

Tests the Coinbase CDP AgentKit client wrapper including:
- Initialization with/without CDP credentials
- Optimistic transaction hash generation
- Simulated and configured payment modes
- Background thread dispatch
- State manager updates
"""

import asyncio
import os
import re
import threading
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Set rate limits high before importing app code
os.environ["MAYA_SESSION_RATE_LIMIT"] = "9999"
os.environ["MAYA_APP_RATE_LIMIT"] = "9999"
os.environ["MAYA_BURST_LIMIT"] = "9999"

from src.payments.crypto_client import CryptoPaymentClient, DEFAULT_RECEIVER_ADDRESS


pytestmark = pytest.mark.unit


class TestCryptoPaymentClientInit:
    """Test client initialization with various environment configurations."""

    def test_init_without_cdp_keys(self, monkeypatch):
        """Client should report is_configured=False when keys are missing."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        monkeypatch.delenv("CDP_MERCHANT_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("CDP_RECEIVER_ADDRESS", raising=False)

        client = CryptoPaymentClient()

        assert client.is_configured is False
        assert client.api_key_id is None
        assert client.api_key_secret is None
        assert client.merchant_private_key is None
        assert client.receiver_address == DEFAULT_RECEIVER_ADDRESS

    def test_init_with_cdp_keys(self, monkeypatch):
        """Client should report is_configured=True when both keys are set."""
        monkeypatch.setenv("CDP_API_KEY_ID", "test_key_id")
        monkeypatch.setenv("CDP_API_KEY_SECRET", "test_key_secret")

        client = CryptoPaymentClient()

        assert client.is_configured is True
        assert client.api_key_id == "test_key_id"
        assert client.api_key_secret == "test_key_secret"

    def test_init_with_partial_keys(self, monkeypatch):
        """Client should report is_configured=False when only one key is set."""
        monkeypatch.setenv("CDP_API_KEY_ID", "test_key_id")
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)

        client = CryptoPaymentClient()

        assert client.is_configured is False

    def test_init_with_custom_receiver(self, monkeypatch):
        """Client should use custom receiver address when configured."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        monkeypatch.setenv("CDP_RECEIVER_ADDRESS", "0xCustomAddress123")

        client = CryptoPaymentClient()

        assert client.receiver_address == "0xCustomAddress123"

    def test_init_with_merchant_key(self, monkeypatch):
        """Client should store merchant private key when provided."""
        monkeypatch.setenv("CDP_API_KEY_ID", "test_key_id")
        monkeypatch.setenv("CDP_API_KEY_SECRET", "test_key_secret")
        monkeypatch.setenv("CDP_MERCHANT_PRIVATE_KEY", "0xMerchantKey")

        client = CryptoPaymentClient()

        assert client.merchant_private_key == "0xMerchantKey"


class TestGenerateTxHash:
    """Test transaction hash generation."""

    def test_hash_format(self, monkeypatch):
        """Generated hash should be a 66-char hex string starting with 0x."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        tx_hash = client.generate_tx_hash()

        assert tx_hash.startswith("0x")
        assert len(tx_hash) == 66
        # Validate hex characters after 0x prefix
        assert re.match(r"^0x[0-9a-f]{64}$", tx_hash)

    def test_hash_uniqueness(self, monkeypatch):
        """Each call should generate a unique hash."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        hashes = {client.generate_tx_hash() for _ in range(100)}

        assert len(hashes) == 100, "Generated hashes should be unique"


class TestProcessPaymentOptimistically:
    """Test the optimistic payment processing flow."""

    def test_simulated_mode_returns_correct_structure(self, monkeypatch):
        """In simulation mode, should return tx_hash, url, is_simulated=True."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        result = client.process_payment_optimistically(
            amount=13.00, session_id="test_session_123"
        )

        assert "tx_hash" in result
        assert "url" in result
        assert "is_simulated" in result
        assert result["is_simulated"] is True
        assert result["tx_hash"].startswith("0x")
        assert len(result["tx_hash"]) == 66

    def test_basescan_url_format(self, monkeypatch):
        """URL should point to Base Sepolia explorer with the tx hash."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        result = client.process_payment_optimistically(
            amount=13.00, session_id="test_session"
        )

        expected_url = f"https://sepolia.basescan.org/tx/{result['tx_hash']}"
        assert result["url"] == expected_url

    def test_configured_mode_returns_not_simulated(self, monkeypatch):
        """When CDP keys are set, is_simulated should be False."""
        monkeypatch.setenv("CDP_API_KEY_ID", "test_key_id")
        monkeypatch.setenv("CDP_API_KEY_SECRET", "test_key_secret")
        client = CryptoPaymentClient()

        # Mock threading to prevent actual background execution
        with patch("src.payments.crypto_client.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            # Simulate no running event loop (triggers thread fallback)
            with patch("src.payments.crypto_client.asyncio.get_running_loop",
                       side_effect=RuntimeError("no running loop")):
                result = client.process_payment_optimistically(
                    amount=25.00, session_id="test_configured"
                )

        assert result["is_simulated"] is False

    def test_simulated_mode_spawns_daemon_thread(self, monkeypatch):
        """Simulated mode should start a daemon background thread."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        started_threads = []
        original_thread_init = threading.Thread.__init__

        class TrackingThread(threading.Thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                started_threads.append(self)

            def start(self):
                # Don't actually start the thread in tests
                pass

        with patch("src.payments.crypto_client.threading.Thread", TrackingThread):
            client.process_payment_optimistically(
                amount=13.00, session_id="test_daemon"
            )

        assert len(started_threads) == 1
        assert started_threads[0].daemon is True

    def test_configured_mode_tries_event_loop_first(self, monkeypatch):
        """When configured, should try asyncio.get_running_loop first."""
        monkeypatch.setenv("CDP_API_KEY_ID", "test_key_id")
        monkeypatch.setenv("CDP_API_KEY_SECRET", "test_key_secret")
        client = CryptoPaymentClient()

        mock_loop = MagicMock()

        with patch("src.payments.crypto_client.asyncio.get_running_loop",
                    return_value=mock_loop):
            client.process_payment_optimistically(
                amount=25.00, session_id="test_loop"
            )

        mock_loop.create_task.assert_called_once()

    def test_configured_mode_falls_back_to_thread(self, monkeypatch):
        """When no event loop exists, should fall back to a thread."""
        monkeypatch.setenv("CDP_API_KEY_ID", "test_key_id")
        monkeypatch.setenv("CDP_API_KEY_SECRET", "test_key_secret")
        client = CryptoPaymentClient()

        with patch("src.payments.crypto_client.asyncio.get_running_loop",
                    side_effect=RuntimeError("no running loop")):
            with patch("src.payments.crypto_client.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                client.process_payment_optimistically(
                    amount=25.00, session_id="test_fallback"
                )

                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()


class TestSimulatePaymentLifecycle:
    """Test the simulated payment lifecycle coroutine."""

    def test_normal_amount_succeeds(self, monkeypatch):
        """Non-$99.99 amounts should result in 'completed' status."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        with patch.object(client, "_update_payment_status") as mock_update:
            asyncio.run(
                client._simulate_payment_lifecycle(13.00, "test_sess", "0xhash")
            )

            mock_update.assert_called_once_with("test_sess", "completed")

    def test_99_99_triggers_failure(self, monkeypatch):
        """Amount of $99.99 should trigger a failure status."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        with patch.object(client, "_update_payment_status") as mock_update:
            asyncio.run(
                client._simulate_payment_lifecycle(99.99, "test_fail", "0xhash")
            )

            mock_update.assert_called_once_with("test_fail", "failed")

    def test_near_99_99_triggers_failure(self, monkeypatch):
        """Amount close to $99.99 (within 0.01) should also trigger failure."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        with patch.object(client, "_update_payment_status") as mock_update:
            asyncio.run(
                client._simulate_payment_lifecycle(99.989, "test_near", "0xhash")
            )

            mock_update.assert_called_once_with("test_near", "failed")


class TestUpdatePaymentStatus:
    """Test the state manager update helper."""

    def test_updates_state_successfully(self, monkeypatch):
        """Should call update_payment_state with correct args."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        mock_store = {}
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch("src.llm.tools.get_global_store", return_value=mock_store), \
             patch("src.utils.state_manager.get_session_lock", return_value=mock_lock), \
             patch("src.utils.state_manager.update_payment_state") as mock_update:

            client._update_payment_status("test_session", "completed")

            mock_update.assert_called_once_with("test_session", mock_store, {
                "payment_status": "completed"
            })

    def test_handles_update_failure_gracefully(self, monkeypatch):
        """Should catch and log exceptions from state manager."""
        monkeypatch.delenv("CDP_API_KEY_ID", raising=False)
        monkeypatch.delenv("CDP_API_KEY_SECRET", raising=False)
        client = CryptoPaymentClient()

        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch("src.llm.tools.get_global_store", return_value={}), \
             patch("src.utils.state_manager.get_session_lock", return_value=mock_lock), \
             patch("src.utils.state_manager.update_payment_state",
                   side_effect=Exception("State update failed")):

            # Should not raise
            client._update_payment_status("test_session", "failed")


class TestDefaultReceiverAddress:
    """Test the default receiver address constant."""

    def test_default_address_is_valid_hex(self):
        """The default receiver address should be a valid Ethereum address."""
        assert DEFAULT_RECEIVER_ADDRESS.startswith("0x")
        assert len(DEFAULT_RECEIVER_ADDRESS) == 42
