#!/usr/bin/env python3
"""
Unit tests for generation pathways using google-genai:
- src.llm.client.call_gemini_api
- src.rag.pipeline.generate_augmented_response
- src.rag.memvid_pipeline.generate_memvid_response
"""

from types import SimpleNamespace as NS

import pytest

import src.llm.client as llm_client
import src.rag.memvid_pipeline as memvid_pipeline

class _FakeModels:
    """Fake models attribute for a mock genai.Client."""
    def __init__(self):
        self.call_count = 0
        self.call_history = []
        self.last_call = None

    def generate_content(self, model: str, contents=None, config=None):
        self.call_count += 1
        call_record = {
            'model': model,
            'contents': contents,
            'config': config,
        }
        self.call_history.append(call_record)
        self.last_call = call_record
        return NS(text="OK")


@pytest.fixture
def mock_genai_client(monkeypatch):
    """Fixture that mocks get_genai_client to return a fake client."""
    mock_data = {'key': None, 'client': None}
    fake_models = _FakeModels()

    def fake_get_genai_client(api_key: str):
        mock_data['key'] = api_key
        client = NS(models=fake_models)
        mock_data['client'] = client
        return client

    monkeypatch.setattr('src.llm.client.get_genai_client', fake_get_genai_client)

    monkeypatch.setattr('src.rag.memvid_pipeline.get_genai_client', fake_get_genai_client)

    return {'data': mock_data, 'models': fake_models}


def test_call_gemini_api_uses_genai_client(mock_genai_client, monkeypatch):
    # Arrange
    monkeypatch.setattr(llm_client, 'get_model_name', lambda: 'gemini-3.0-flash', raising=False)

    prompt = [{"role": "user", "content": "Hello"}]
    cfg = {"temperature": 0.7, "top_p": 0.9, "top_k": 1, "max_output_tokens": 128}

    # Act
    resp = llm_client.call_gemini_api(prompt_content=prompt, config=cfg, api_key='k')

    # Assert
    assert getattr(resp, 'text', None) == "OK"
    assert mock_genai_client['data']['key'] == 'k'
    models = mock_genai_client['models']
    assert models.call_count == 1, "Expected exactly one API call"
    assert models.last_call is not None
    assert models.last_call['model'] == 'gemini-3.0-flash'
    assert models.last_call['contents'] == prompt
    assert models.last_call['config'] is not None

    # Verify config values match the input cfg
    passed_config = models.last_call['config']
    assert getattr(passed_config, 'temperature', None) == cfg['temperature']
    assert getattr(passed_config, 'top_p', None) == cfg['top_p']
    assert getattr(passed_config, 'top_k', None) == cfg['top_k']
    assert getattr(passed_config, 'max_output_tokens', None) == \
        cfg['max_output_tokens']





def test_memvid_pipeline_generate_response(mock_genai_client):
    # Act
    out = memvid_pipeline.generate_memvid_response(
        query_text="Hi",
        retrieved_documents=["mem1", "mem2"],
        api_key='xyz',
        model_version='gemini-3.0-flash'
    )

    # Assert
    assert out == "OK"
    assert mock_genai_client['data']['key'] == 'xyz'
    models = mock_genai_client['models']
    assert models.call_count == 1, "Expected exactly one API call"
    assert models.last_call['model'] == 'gemini-3.0-flash'

    # Verify Memvid prompt structure and document formatting
    memvid_prompt_contents = models.last_call['contents']
    assert isinstance(memvid_prompt_contents, str), f"Memvid prompt contents should be string, got {type(memvid_prompt_contents)}"

    # Check that both documents are present
    assert 'mem1' in memvid_prompt_contents, "Document 'mem1' should be present in Memvid prompt"
    assert 'mem2' in memvid_prompt_contents, "Document 'mem2' should be present in Memvid prompt"

    # Verify Memvid document joining format (pipe separation)
    insights_start = memvid_prompt_contents.find("relevant insights:")
    question_start = memvid_prompt_contents.find("Question:")
    assert insights_start != -1 and question_start != -1, "Required sections not found in Memvid prompt"
    insights_section = memvid_prompt_contents[insights_start:question_start]
    assert "mem1 | mem2" in insights_section, "Memvid documents should be pipe-separated (mem1 | mem2)"

    # Verify Memvid-specific structure elements
    assert "video memory" in memvid_prompt_contents, "Memvid prompt should reference 'video memory'"
    assert "relevant insights:" in memvid_prompt_contents, "Memvid prompt should contain 'relevant insights:' section"
    assert "Question:" in memvid_prompt_contents, "Memvid prompt should contain 'Question:' section header"
    assert "Answer:" in memvid_prompt_contents, "Memvid prompt should contain 'Answer:' section header"
    assert "Maya" in memvid_prompt_contents, "Memvid prompt should contain bartender name 'Maya'"
    assert "MOK 5-ha" in memvid_prompt_contents, "Memvid prompt should contain bar name 'MOK 5-ha'"

    # Ensure documents are distinct and appear exactly once each
    mem1_occurrences = memvid_prompt_contents.count('mem1')
    assert mem1_occurrences == 1, f"Document 'mem1' should appear exactly once, found {mem1_occurrences} times"
    mem2_occurrences = memvid_prompt_contents.count('mem2')
    assert mem2_occurrences == 1, f"Document 'mem2' should appear exactly once, found {mem2_occurrences} times"

    # Verify proper section ordering for Memvid
    insights_pos = memvid_prompt_contents.find("relevant insights:")
    question_pos = memvid_prompt_contents.find("Question:")
    answer_pos = memvid_prompt_contents.find("Answer:")
    assert insights_pos < question_pos < answer_pos, "Memvid sections should be in correct order: Insights -> Question -> Answer"
