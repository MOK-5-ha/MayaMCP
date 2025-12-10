#!/usr/bin/env python3
"""
Pytest-based tests for TTS text cleaning functionality
"""

import pytest

from src.voice.tts import clean_text_for_tts


class TestTTSCleaning:
    """Test suite for TTS text cleaning"""
    
    @pytest.mark.parametrize("input_text,expected_removed,expected_kept", [
        # Asterisk removal
        (
            "Welcome to *MOK 5-ha*! How can I help you today?",
            ["*"],
            ["!", "?"]
        ),
        # Multiple asterisks
        (
            "This is **really** important and ***very*** exciting!",
            ["*"],
            ["!"]
        ),
        # Markdown formatting
        (
            "Here's your `whiskey on the rocks` with **ice** and _garnish_",
            ["`", "*", "_"],
            []
        ),
        # Brackets and symbols
        (
            "Your order [whiskey] costs $15 & includes {ice} <cold>",
            ["[", "]", "$", "&", "{", "}", "<", ">"],
            []
        ),
        # Natural punctuation (should keep)
        (
            "Hello! How are you today? I'm fine, thanks.",
            [],
            ["!", "?", ",", "."]
        ),
    ])
    def test_punctuation_removal(self, input_text, expected_removed, expected_kept):
        """Test that problematic punctuation is removed while preserving natural speech punctuation"""
        result = clean_text_for_tts(input_text)
        
        for char in expected_removed:
            assert char not in result, f"Character '{char}' should have been removed from '{result}'"
        
        for char in expected_kept:
            assert char in result, f"Character '{char}' should have been kept in '{result}'"
    
    def test_mok_5_ha_pronunciation(self):
        """Test that MOK 5-ha is replaced with Moksha for pronunciation"""
        test_cases = [
            "Welcome to MOK 5-ha, the finest bar!",
            "MOK 5-ha is a great place",
            "Come visit mok 5-ha today"
        ]
        
        for input_text in test_cases:
            result = clean_text_for_tts(input_text)
            assert "Moksha" in result, f"MOK 5-ha should be replaced with Moksha in '{result}'"
            assert "MOK 5-ha" not in result and "mok 5-ha" not in result, f"Original text should be replaced in '{result}'"
    
    def test_whitespace_cleanup(self):
        """Test that extra whitespace is cleaned up properly"""
        input_text = "Hello   ***world***   with    multiple    spaces!"
        result = clean_text_for_tts(input_text)
        
        # Should not have multiple consecutive spaces
        assert "  " not in result, f"Should not have multiple spaces in '{result}'"
        # Should be trimmed
        assert result == result.strip(), f"Result should be trimmed: '{result}'"
    
    def test_empty_and_none_input(self):
        """Test handling of empty or None inputs"""
        assert clean_text_for_tts("") == ""
        assert clean_text_for_tts(None) is None
        assert clean_text_for_tts("   ") == ""
    
    def test_complex_mixed_punctuation(self):
        """Test complex scenarios with mixed punctuation"""
        input_text = "***Welcome*** to @MOK 5-ha! Your ##special## drink costs $12.50."
        result = clean_text_for_tts(input_text)
        
        # Should remove problematic punctuation
        for char in ["*", "@", "#", "$"]:
            assert char not in result, f"Problematic punctuation '{char}' should be removed"
        
        # Should keep natural punctuation
        for char in ["!", "."]:
            assert char in result, f"Natural punctuation '{char}' should be kept"
        
        # Should replace MOK 5-ha
        assert "Moksha" in result
        assert "MOK 5-ha" not in result
    
    def test_no_changes_needed(self):
        """Test text that doesn't need any cleaning"""
        input_text = "Hello! How are you today? I'm fine, thanks."
        result = clean_text_for_tts(input_text)
        
        # Should be identical if no problematic punctuation
        assert result == input_text
    
    @pytest.mark.parametrize("problematic_char", [
        "*", "#", "_", "`", "[", "]", "{", "}", "<", ">", "~", "^", "=", "|", "\\", "@", "&", "%", "$"
    ])
    def test_individual_punctuation_removal(self, problematic_char):
        """Test that each problematic punctuation character is removed"""
        input_text = f"Hello {problematic_char}world{problematic_char} test!"
        result = clean_text_for_tts(input_text)
        
        assert problematic_char not in result, f"Character '{problematic_char}' should be removed"
        assert "Hello" in result and "world" in result and "test" in result, "Word content should be preserved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])