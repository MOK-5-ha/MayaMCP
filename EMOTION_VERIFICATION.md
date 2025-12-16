# Emotion Verification Guide

This document outlines the manual verification process for Maya's emotion system. It is designed to ensure that the LLM correctly classifies user intent and outputs the appropriate `[STATE: ...]` tags.

## Observability Mechanism

Maya's emotional state is determined by the `[STATE: emotion]` tag returned in the raw LLM response.
To observe this:
1.  **Check Logs**: The application logs the `Final agent response` in `src/conversation/processor.py` *before* the tag is stripped (in some debug contexts) or you can check the `logger.info` output.
2.  **UI Behavior**: The primary verification is visual—does the avatar change to the correct video file?

## Test Cases

Run through the following scenarios to verify each state.

| Target State | User Input Trigger | Expected Response Properties |
| :--- | :--- | :--- |
| **Neutral** | "Hello Maya." / "What is your name?" | Friendly, calm response. Default state. |
| **Happy** | "This drink is delicious!" / "You're great at your job." | Enthusiastic thanks. Tag: `[STATE: happy]` |
| **Flustered** | "You have beautiful eyes." / "Are you single?" | Shy, deflected compliment. Tag: `[STATE: flustered]` |
| **Thinking** | "What do you recommend for a cold night?" / "Surprise me." | Pause/filler words ("Hmm...", "Let me see"). Tag: `[STATE: thinking]` |
| **Mixing** | "I'll have a Martini." (Order placement) | Confirmation of order. Tag: `[STATE: mixing]` (or happy) |
| **Upset** | "You're too slow!" / "This service is terrible." | Firm but professional pushback. Tag: `[STATE: upset]` |

## Debugging & Prompt Iteration

If Maya fails to trigger the correct emotion (e.g., stays Neutral when she should be Flustered):

### 1. Inspect the Raw Output
Check the terminal output where `mayamcp` is running. Look for the log line:
```text
INFO:src.conversation.processor:Final agent response: [STATE: ???] ...
```
If the tag is missing or incorrect, the LLM is not following the system instruction for that specific context.

### 2. Adjusting Requirements
Open `src/llm/prompts.py` and modify the **EMOTION TAGGING INSTRUCTIONS** section.
*   **Fix**: Add a specific example closer to the failing case.
    *   *Example*: If "You're slow" resulted in `neutral`, add `"- [STATE: upset] \"I'm moving as fast as I can.\""` to the examples list.

### 3. Versioning
When updating `src/llm/prompts.py`, verify that you haven't regressed other states. Run the full suite of test cases above after any prompt change.
