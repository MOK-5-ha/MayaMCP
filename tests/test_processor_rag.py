import types
from types import SimpleNamespace
import pytest

from src.conversation import processor as proc
from langchain_core.messages import AIMessage


class DummyLLM:
    def __init__(self, content="base response"):
        self._content = content
    def invoke(self, messages):
        # Return a simple AIMessage with text content and no tool_calls
        return AIMessage(content=self._content)


@pytest.fixture
def stub_get_menu(monkeypatch):
    # Ensure get_menu.invoke works without LangChain runtime complexities
    from src import llm as llm_pkg
    from src.llm import tools as tools_mod
    stub = SimpleNamespace(invoke=lambda _: "MENU: test")
    monkeypatch.setattr(tools_mod, "get_menu", stub, raising=True)
    yield


def test_rag_short_circuits_when_components_missing(monkeypatch, stub_get_menu):
    """When RAG components are unavailable, the RAG path should be skipped early without calling pipelines."""
    # Ensure casual conversation -> should_use_rag True
    monkeypatch.setattr("src.utils.helpers.is_casual_conversation", lambda _: True, raising=True)

    # Ensure if accidentally called, pipelines would fail the test
    monkeypatch.setattr(proc, "memvid_rag_pipeline", lambda **kwargs: (_ for _ in ()).throw(AssertionError("memvid should not be called")), raising=False)
    monkeypatch.setattr(proc, "rag_pipeline", lambda **kwargs: (_ for _ in ()).throw(AssertionError("faiss should not be called")), raising=False)

    llm = DummyLLM("llm base")
    user_input = "How's your day going?"

    # All RAG components missing -> should skip RAG enhancement
    response_text, _, _, _, _ = proc.process_order(
        user_input_text=user_input,
        current_session_history=[],
        llm=llm,
        rag_index=None,
        rag_documents=None,
        rag_retriever=None,
        api_key="dummy-key",
    )

    assert response_text == "llm base"


def test_safe_length_check_with_non_sized_rag_response(monkeypatch, stub_get_menu):
    """If the RAG pipeline returns a non-sized object, process_order should not raise and should keep the original response."""
    # Ensure casual conversation -> should_use_rag True
    monkeypatch.setattr("src.utils.helpers.is_casual_conversation", lambda _: True, raising=True)

    # Provide FAISS-style availability and a rag_pipeline that returns a non-sized object
    class NonSized:
        __repr__ = lambda self: "<NonSized>"
    def rag_pipeline_stub(**kwargs):
        return NonSized()

    monkeypatch.setattr(proc, "memvid_rag_pipeline", None, raising=False)
    monkeypatch.setattr(proc, "rag_pipeline", rag_pipeline_stub, raising=False)

    llm = DummyLLM("base text")
    user_input = "Just chatting about the weather."

    response_text, _, _, _, _ = proc.process_order(
        user_input_text=user_input,
        current_session_history=[],
        llm=llm,
        rag_index=object(),
        rag_documents=["doc1"],
        rag_retriever=None,
        api_key="dummy-key",
    )

    # Because the RAG result is non-sized, it should NOT replace the base response
    assert response_text == "base text"

