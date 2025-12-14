"""Unit tests for session context lifecycle in LLM tools."""

import threading
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.llm.tools import (
    get_current_session,
    set_current_session,
    clear_current_session,
    _session_context
)


class TestSessionContextBasics:
    """Test basic session context operations."""

    def test_get_current_session_returns_none_by_default(self):
        """Test that get_current_session returns None when no session is set."""
        # Clear any existing session first
        clear_current_session()
        
        result = get_current_session()
        
        assert result is None

    def test_set_current_session_stores_session_id(self):
        """Test that set_current_session stores the session ID."""
        test_session_id = "test-session-123"
        
        set_current_session(test_session_id)
        result = get_current_session()
        
        assert result == test_session_id
        
        # Cleanup
        clear_current_session()

    def test_clear_current_session_removes_session_id(self):
        """Test that clear_current_session removes the session ID."""
        set_current_session("test-session-456")
        
        clear_current_session()
        result = get_current_session()
        
        assert result is None

    def test_set_current_session_with_none_clears_session(self):
        """Test that setting session to None clears it."""
        set_current_session("test-session-789")
        
        set_current_session(None)
        result = get_current_session()
        
        assert result is None

    def test_set_current_session_overwrites_previous(self):
        """Test that setting a new session overwrites the previous one."""
        set_current_session("session-1")
        set_current_session("session-2")
        
        result = get_current_session()
        
        assert result == "session-2"
        
        # Cleanup
        clear_current_session()


class TestSessionContextThreadIsolation:
    """Test that session context is thread-local."""

    def test_session_context_is_thread_local(self):
        """Test that session context is isolated between threads."""
        results = {}
        
        def thread_func(thread_id, session_id):
            set_current_session(session_id)
            # Small delay to allow interleaving
            import time
            time.sleep(0.01)
            results[thread_id] = get_current_session()
            clear_current_session()
        
        # Create threads with different session IDs
        thread1 = threading.Thread(target=thread_func, args=("t1", "session-thread-1"))
        thread2 = threading.Thread(target=thread_func, args=("t2", "session-thread-2"))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Each thread should have seen its own session ID
        assert results["t1"] == "session-thread-1"
        assert results["t2"] == "session-thread-2"

    def test_main_thread_session_not_affected_by_other_threads(self):
        """Test that main thread session is not affected by other threads."""
        set_current_session("main-session")
        
        def other_thread_func():
            set_current_session("other-session")
            clear_current_session()
        
        other_thread = threading.Thread(target=other_thread_func)
        other_thread.start()
        other_thread.join()
        
        # Main thread session should be unchanged
        assert get_current_session() == "main-session"
        
        # Cleanup
        clear_current_session()


class TestSessionContextInProcessor:
    """Test session context integration with processor."""

    @patch('src.conversation.processor.ConversationPhaseManager')
    @patch('src.conversation.processor.get_current_order_state')
    @patch('src.conversation.processor.detect_speech_acts')
    @patch('src.conversation.processor.detect_order_inquiry')
    def test_process_order_sets_session_context(
        self, 
        mock_detect_order, 
        mock_detect_speech,
        mock_get_order_state,
        mock_phase_manager
    ):
        """Test that process_order sets the session context before processing."""
        from src.conversation.processor import process_order
        from src.llm.tools import get_current_session, clear_current_session
        
        # Setup mocks
        mock_detect_speech.return_value = {'intent': None, 'confidence': 0, 'speech_act': None}
        mock_detect_order.return_value = {'intent': 'show_order', 'confidence': 0.9}
        mock_get_order_state.return_value = []
        
        mock_pm_instance = MagicMock()
        mock_pm_instance.get_current_phase.return_value = 'greeting'
        mock_phase_manager.return_value = mock_pm_instance
        
        # Create a mock LLM
        mock_llm = MagicMock()
        
        # Clear any existing session
        clear_current_session()
        
        # Call process_order
        test_session_id = "test-processor-session"
        process_order(
            user_input_text="show my order",
            current_session_history=[],
            llm=mock_llm,
            session_id=test_session_id
        )
        
        # After process_order completes, session should be cleared
        assert get_current_session() is None

    @patch('src.conversation.processor.ConversationPhaseManager')
    @patch('src.conversation.processor.get_current_order_state')
    @patch('src.conversation.processor.detect_speech_acts')
    @patch('src.conversation.processor.detect_order_inquiry')
    def test_process_order_clears_session_on_error(
        self,
        mock_detect_order,
        mock_detect_speech,
        mock_get_order_state,
        mock_phase_manager
    ):
        """Test that process_order clears session context even on error."""
        from src.conversation.processor import process_order
        from src.llm.tools import get_current_session, clear_current_session
        
        # Setup mocks to cause an error in the try block
        mock_detect_speech.return_value = {'intent': None, 'confidence': 0, 'speech_act': None}
        mock_detect_order.return_value = {'intent': None, 'confidence': 0}
        mock_get_order_state.return_value = []
        
        mock_pm_instance = MagicMock()
        mock_pm_instance.get_current_phase.return_value = 'greeting'
        mock_phase_manager.return_value = mock_pm_instance
        
        # Create a mock LLM that raises an exception
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Test error")
        
        # Clear any existing session
        clear_current_session()
        
        # Call process_order - it should handle the error gracefully
        test_session_id = "test-error-session"
        result = process_order(
            user_input_text="order something",
            current_session_history=[],
            llm=mock_llm,
            session_id=test_session_id
        )
        
        # Session should be cleared even after error
        assert get_current_session() is None
        
        # Should return an error message (various phrasings are acceptable)
        error_indicators = ["error", "sorry", "trouble", "problem", "issue"]
        assert any(indicator in result[0].lower() for indicator in error_indicators)


class TestLegacyBehavior:
    """Test that legacy code continues to work without session context."""

    def test_tools_work_without_session_context(self):
        """Test that existing tools work when no session context is set."""
        from src.llm.tools import get_menu
        
        # Ensure no session is set
        clear_current_session()
        
        # get_menu should work without session context
        result = get_menu.invoke({})
        
        assert "MENU:" in result
        assert "Martini" in result

    @patch('src.llm.tools.get_current_order_state')
    def test_get_order_works_without_session_context(self, mock_get_order_state):
        """Test that get_order works when no session context is set."""
        from src.llm.tools import get_order
        
        # Ensure no session is set
        clear_current_session()
        
        # Setup mock
        mock_get_order_state.return_value = []
        
        # get_order should work without session context
        result = get_order.invoke({})
        
        assert "empty" in result.lower()
