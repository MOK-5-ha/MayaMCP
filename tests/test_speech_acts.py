#!/usr/bin/env python3
"""
Pytest-based tests for speech act detection functionality
"""

import pytest
import sys
import os

from src.utils.helpers import detect_speech_acts


class TestSpeechActDetection:
    """Test suite for speech act-based intent detection"""
    
    @pytest.mark.parametrize("user_input,context,expected_intent,expected_speech_act", [
        # Commissive speech acts (order confirmations)
        (
            "I can certainly get you that whiskey on the rocks",
            ["Hello there, Maya. Can I have a whiskey on the rocks?"],
            "order_confirmation",
            "commissive"
        ),
        (
            "Absolutely, I'll make that for you right away", 
            ["Can I get a Manhattan?", "With a cherry please"],
            "order_confirmation",
            "commissive"
        ),
        (
            "Sure, coming right up",
            ["I'd like a beer please"],
            "order_confirmation", 
            "commissive"
        ),
        
        # Assertive speech acts (order confirmations)
        (
            "Here is your whiskey on the rocks",
            ["I ordered a whiskey on the rocks"],
            "order_confirmation",
            "assertive"
        ),
        (
            "This is your Manhattan with a cherry",
            ["Manhattan with cherry please"],
            "order_confirmation",
            "assertive"
        ),
        
        # Directive speech acts (order requests)
        (
            "Can you make me a whiskey on the rocks",
            [],
            "order_request",
            "directive"
        ),
        (
            "I'd like a cocktail please",
            [],
            "order_request", 
            "directive"
        ),
        
        # Non-order conversations
        (
            "How's your day going?",
            [],
            None,
            None
        ),
        (
            "What's the weather like?",
            ["Nice to meet you"],
            None,
            None
        )
    ])
    def test_speech_act_detection(self, user_input, context, expected_intent, expected_speech_act):
        """Test speech act detection with various conversation scenarios"""
        result = detect_speech_acts(user_input, context)
        
        assert result['intent'] == expected_intent, f"Expected intent {expected_intent}, got {result['intent']}"
        assert result['speech_act'] == expected_speech_act, f"Expected speech act {expected_speech_act}, got {result['speech_act']}"
    
    def test_commissive_with_drink_context(self):
        """Test commissive speech acts with drink context extraction"""
        user_input = "I can certainly get you that whiskey on the rocks"
        context = ["Hello there, Maya. Can I have a whiskey on the rocks?"]
        
        result = detect_speech_acts(user_input, context)
        
        assert result['intent'] == 'order_confirmation'
        assert result['speech_act'] == 'commissive'
        assert result['confidence'] >= 0.8
        assert 'drink_context' in result and result['drink_context'] is not None
        assert 'whiskey' in result['drink_context']
        assert 'rocks' in result['drink_context']
    
    def test_confidence_scoring(self):
        """Test that confidence scores are calculated appropriately"""
        # High confidence case with both pattern and context
        high_conf_result = detect_speech_acts(
            "I can get you that whiskey", 
            ["Can I have a whiskey?"]
        )
        
        # Lower confidence case with pattern but no context
        low_conf_result = detect_speech_acts(
            "I can get you that",
            []
        )
        
        # Both cases should have detected an intent
        assert high_conf_result['intent'] is not None, "High confidence case should detect an intent"
        assert low_conf_result['intent'] is not None, "Low confidence case should detect an intent"
        assert high_conf_result['confidence'] > low_conf_result['confidence'], \
            f"Expected high confidence ({high_conf_result['confidence']}) > low confidence ({low_conf_result['confidence']})"
    
    def test_empty_input_handling(self):
        """Test handling of empty or invalid inputs"""
        result = detect_speech_acts("", [])
        assert result['intent'] is None
        assert result['confidence'] == 0
        
        result = detect_speech_acts("   ", [])
        assert result['intent'] is None
        assert result['confidence'] == 0
    
    def test_drink_context_extraction(self):
        """Test extraction of drink context from conversation history"""
        context = [
            "I'd like a whiskey on the rocks",
            "Make it a double",
            "Thank you"
        ]
        
        result = detect_speech_acts("I can get that for you", context)
        
        assert result['drink_context'] is not None, "Should extract drink context from conversation history"
        assert 'whiskey' in result['drink_context'], "Should extract 'whiskey' from context"
        assert 'rocks' in result['drink_context'], "Should extract 'rocks' from context"
    
    def test_assertive_speech_act_mapping(self):
        """Test that assertive speech acts map to order_confirmation"""
        result = detect_speech_acts(
            "Here is your drink",
        # Should detect assertive pattern and map to order_confirmation
        assert result['speech_act'] == 'assertive', "Should detect assertive speech act for 'Here is your drink'"
        assert result['intent'] == 'order_confirmation', "Assertive speech acts should map to order_confirmation"
        
        # Should detect assertive pattern and map to order_confirmation
        if result['speech_act'] == 'assertive':
            assert result['intent'] == 'order_confirmation'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])