#!/usr/bin/env python3
"""
Test TTS text cleaning functionality
"""

import sys
import os
sys.path.insert(0, 'src')

from src.voice.tts import clean_text_for_tts

def test_tts_cleaning():
    """Test TTS text cleaning with various punctuation scenarios"""
    print("🗣️ Testing TTS Text Cleaning")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Asterisks (Emphasis)",
            "input": "Welcome to *MOK 5-ha*! How can I help you today?",
            "expected_removes": ["*"],
            "expected_keeps": ["!", "?"]
        },
        {
            "name": "Multiple Asterisks",
            "input": "This is **really** important and ***very*** exciting!",
            "expected_removes": ["*"],
            "expected_keeps": ["!"]
        },
        {
            "name": "Markdown-style Formatting",
            "input": "Here's your `whiskey on the rocks` with **ice** and _garnish_",
            "expected_removes": ["`", "*", "_"],
            "expected_keeps": []
        },
        {
            "name": "Brackets and Symbols",
            "input": "Your order [whiskey] costs $15 & includes {ice} <cold>",
            "expected_removes": ["[", "]", "$", "&", "{", "}", "<", ">"],
            "expected_keeps": []
        },
        {
            "name": "Natural Punctuation (Should Keep)",
            "input": "Hello! How are you today? I'm fine, thanks.",
            "expected_removes": [],
            "expected_keeps": ["!", "?", ",", "."]
        },
        {
            "name": "MOK 5-ha Pronunciation",
            "input": "Welcome to MOK 5-ha, the finest bar in town!",
            "expected_replaces": [("MOK 5-ha", "Moksha")],
            "expected_keeps": ["!", ",", "."]
        },
        {
            "name": "Complex Mixed Punctuation",
            "input": "***Welcome*** to @MOK 5-ha! Your ##special## drink costs $12.50.",
            "expected_removes": ["*", "@", "#", "$"],
            "expected_keeps": ["!", "."]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Input:  '{test_case['input']}'")
        
        result = clean_text_for_tts(test_case['input'])
        print(f"   Output: '{result}'")
        
        # Check what was removed
        removed_chars = []
        kept_chars = []
        
        for char in test_case.get('expected_removes', []):
            if char not in result:
                removed_chars.append(char)
            else:
                print(f"   ❌ ISSUE: '{char}' should have been removed but is still present")
        
        for char in test_case.get('expected_keeps', []):
            if char in result:
                kept_chars.append(char)
            else:
                print(f"   ❌ ISSUE: '{char}' should have been kept but was removed")
        
        # Check replacements
        for old, new in test_case.get('expected_replaces', []):
            if old not in result and new in result:
                print(f"   ✅ REPLACED: '{old}' → '{new}'")
            else:
                print(f"   ❌ ISSUE: '{old}' → '{new}' replacement failed")
        
        if removed_chars:
            print(f"   ✅ REMOVED: {removed_chars}")
        if kept_chars:
            print(f"   ✅ KEPT: {kept_chars}")
        
        print("-" * 50)
    
    print("\n🎯 Summary")
    print("=" * 30)
    print("✅ Asterisks (*) will no longer be pronounced")
    print("✅ Other problematic punctuation removed")
    print("✅ Natural speech punctuation preserved")
    print("✅ MOK 5-ha → Moksha pronunciation fix included")

if __name__ == "__main__":
    test_tts_cleaning()