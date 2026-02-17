#!/usr/bin/env python3
"""
Unit tests for src.rag.embeddings (google-genai based) parsing paths.
"""

from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

import src.rag.embeddings as emb


def _make_mock_client(embed_return):
    """Create a mock genai client whose models.embed_content returns *embed_return*."""
    client = MagicMock()
    client.models.embed_content.return_value = embed_return
    return client


def _patch_client(monkeypatch, embed_return):
    """Patch _get_embed_client to return a mock client with the given embed response."""
    client = _make_mock_client(embed_return)
    monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)
    return client


def test_embedding_parsing_object_with_values(monkeypatch):
    _patch_client(monkeypatch, NS(embeddings=[NS(values=[0.1, 0.2, 0.3])]))
    vec = emb.get_embedding("hello world")
    assert vec == [0.1, 0.2, 0.3]


def test_embedding_parsing_object_list(monkeypatch):
    # embeddings[0] is a plain list (fallback path)
    _patch_client(monkeypatch, NS(embeddings=[[0.4, 0.5]]))
    vec = emb.get_embedding("foo bar", task_type="RETRIEVAL_QUERY")
    assert vec == [0.4, 0.5]


def test_embedding_unexpected_structure(monkeypatch):
    # No 'embeddings' attribute at all
    _patch_client(monkeypatch, NS(foo="bar"))
    vec = emb.get_embedding("unexpected")
    assert vec is None


def test_embedding_empty_embeddings_list(monkeypatch):
    _patch_client(monkeypatch, NS(embeddings=[]))
    vec = emb.get_embedding("empty")
    assert vec is None


def test_embedding_exception_returns_none(monkeypatch):
    client = MagicMock()
    client.models.embed_content.side_effect = Exception("timeout")
    monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)
    vec = emb.get_embedding("will error")
    assert vec is None


def test_embedding_no_api_key(monkeypatch):
    monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: None)
    vec = emb.get_embedding("no key")
    assert vec is None


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
