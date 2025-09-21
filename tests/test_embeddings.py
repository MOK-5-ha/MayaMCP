#!/usr/bin/env python3
"""
Unit tests for src.rag.embeddings (google-generativeai based) parsing paths.
"""

import sys
from types import SimpleNamespace as NS
import pytest

# Ensure 'src' is on sys.path (consistent with other tests in this repo)
sys.path.insert(0, 'src')

import src.rag.embeddings as emb


def _patch_api_key(monkeypatch):
    # Always provide a fake API key
    monkeypatch.setattr('src.config.api_keys.get_google_api_key', lambda: 'dummy-key', raising=False)


def test_embedding_parsing_object_with_values(monkeypatch):
    _patch_api_key(monkeypatch)
    # google.generativeai.embed_content returns an object with .embedding.values
    def fake_embed_content(model: str, content: str, **kwargs):
        return NS(embedding=NS(values=[0.1, 0.2, 0.3]))
    monkeypatch.setattr('google.generativeai.embed_content', fake_embed_content, raising=False)
    vec = emb.get_embedding("hello world")
    assert vec == [0.1, 0.2, 0.3]


def test_embedding_parsing_object_list(monkeypatch):
    _patch_api_key(monkeypatch)
    def fake_embed_content(model: str, content: str, **kwargs):
        return NS(embedding=[0.4, 0.5])
    monkeypatch.setattr('google.generativeai.embed_content', fake_embed_content, raising=False)
    vec = emb.get_embedding("foo bar", task_type="RETRIEVAL_QUERY")
    assert vec == [0.4, 0.5]


def test_embedding_parsing_dict_values(monkeypatch):
    _patch_api_key(monkeypatch)
    def fake_embed_content(model: str, content: str, **kwargs):
        return {"embedding": {"values": [0.6, 0.7]}}
    monkeypatch.setattr('google.generativeai.embed_content', fake_embed_content, raising=False)
    vec = emb.get_embedding("baz qux")
    assert vec == [0.6, 0.7]


def test_embedding_parsing_dict_list(monkeypatch):
    _patch_api_key(monkeypatch)
    def fake_embed_content(model: str, content: str, **kwargs):
        return {"embedding": [0.8, 0.9]}
    monkeypatch.setattr('google.generativeai.embed_content', fake_embed_content, raising=False)
    vec = emb.get_embedding("lorem ipsum")
    assert vec == [0.8, 0.9]


def test_embedding_unexpected_structure(monkeypatch):
    _patch_api_key(monkeypatch)
    def fake_embed_content(model: str, content: str, **kwargs):
        return NS(foo="bar")
    monkeypatch.setattr('google.generativeai.embed_content', fake_embed_content, raising=False)
    vec = emb.get_embedding("unexpected")
    assert vec is None


def test_embedding_exception_returns_none(monkeypatch):
    _patch_api_key(monkeypatch)
    def fake_embed_content(model: str, content: str, **kwargs):
        raise Exception("timeout")
    monkeypatch.setattr('google.generativeai.embed_content', fake_embed_content, raising=False)
    vec = emb.get_embedding("will error")
    assert vec is None


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
