#!/usr/bin/env python3
"""
Test speech act-based intent detection for Maya
"""

import sys
import os
sys.path.insert(0, 'src')

from src.utils.helpers import detect_speech_acts

def test_speech_acts():
    """Test speech act detection with various conversation scenarios"""
    print("🗣️ Testing Speech Act-Based Intent Detection")
    print("=" * 60)
    
    # Test cases from the screenshot scenario
    test_cases = [
        {
            "name": "Commissive Speech Act (Order Confirmation)",
            "user_input": "I can certainly get you that whiskey on the rocks",
            "context": ["Hello there, Maya. Can I have a whiskey on the rocks?"],
            "expected_intent": "order_confirmation"
        },
        {
            "name": "Direct Order Request", 
            "user_input": "I'd like a whiskey on the rocks please",
            "context": [],
            "expected_intent": "order_request"
        },
        {
            "name": "Assertive Speech Act",
            "user_input": "Here is your whiskey on the rocks",
            "context": ["I ordered a whiskey on the rocks"],
            "expected_intent": "order_confirmation"
        },
        {
            "name": "Casual Conversation (No Order)",
            "user_input": "How's your day going?",
            "context": [],
            "expected_intent": None
        },
        {
            "name": "Commissive with Context",
            "user_input": "Absolutely, I'll make that for you right away",
            "context": ["Can I get a Manhattan?", "With a cherry please"],
            "expected_intent": "order_confirmation"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Input: '{test_case['user_input']}'")
        print(f"   Context: {test_case['context']}")
        
        result = detect_speech_acts(test_case['user_input'], test_case['context'])
        
        print(f"   Result: Intent='{result['intent']}', Speech Act='{result['speech_act']}', Confidence={result['confidence']:.2f}")
        print(f"   Drink Context: '{result['drink_context']}'")
        
        # Check if result matches expectation
        expected = test_case['expected_intent']
        actual = result['intent']
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        print(f"   Status: {status} (Expected: {expected})")
        print("-" * 60)
    
    print("\n🎯 Testing Screenshot Scenario")
    print("=" * 40)
    
    # Exact scenario from screenshot
    screenshot_context = [
        "Hello there, Maya. Can I have a whiskey on the rocks?",
        "Thank you so much. What's my bill?"
    ]
    
    maya_response = "I can certainly get you that whiskey on the rocks"
    
    result = detect_speech_acts(maya_response, screenshot_context)
    print(f"Screenshot Input: '{maya_response}'")
    print(f"Context: {screenshot_context}")
    print(f"Detection Result: {result}")
    
    if result['intent'] == 'order_confirmation' and result['confidence'] > 0.4:
        print("✅ SUCCESS: Maya's commissive speech act would now be recognized as order confirmation!")
    else:
        print("❌ ISSUE: Detection failed - needs tuning")

if __name__ == "__main__":
    test_speech_acts()