# Emotion System Architecture

Maya now features an emotion-based animation system that allows her avatar to react dynamically to user inputs. This document details the technical implementation, state management, and asset requirements.

## Overview

The system works by establishing a feedback loop between the LLM's semantic understanding of the conversation and the frontend's visual presentation.

1.  **Input**: User sends a message.
2.  **Processing**: LLM determines the appropriate response and *internal emotional state*.
3.  **Parsing**: The system extracts the emotion tag from the response.
4.  **State Management**: The UI updates the avatar state if a valid emotion is found; otherwise, it persists the current state.
5.  **Rendering**: The corresponding video asset is played.

## LLM Integration

### 1. Prompt Engineering (`src/llm/prompts.py`)
The system prompt has been updated to instruct Maya to classify her own emotional response using a hidden formatting tag.
-   **Instruction**: "Always start your response with an internal emotion tag in the format: `[STATE: emotion]`."
-   **Valid Tags**: `neutral`, `happy`, `flustered`, `thinking`, `mixing`, `upset`.

### 2. Output Parsing (`src/conversation/processor.py`)
The `process_order` function intercepts the raw LLM output before it reaches the user.
-   **Regex**: `r'\[STATE:\s*(\w+)\]'` is used to find the tag.
-   **Cleaning**: The tag is stripped from the final text sent to the chat interface.
-   **Return**: The extracted emotion string (lower cased) is returned alongside the text. If no tag is found, it returns `None` (indicating "no change").

## State Persistence & Error Handling

To prevent visual glitches (flickering to default) or jarring transitions, the system implements robust state persistence in `src/ui/handlers.py` and `src/ui/launcher.py`.

### Logic Flow
1.  **Initial State**: Standard `neutral` or static avatar.
2.  **Valid Update**: If the LLM returns a valid emotion (e.g., "happy") AND the corresponding asset exists, the state is updated.
3.  **Implicit State**: If the LLM returns `None` (no tag found), the **previous valid state is maintained**. This allows Maya to stay "flustered" for multiple turns if the conversation continues in that vein without explicit retagging.
4.  **Error Handling**: If an exception occurs (network error, processing error), the state is **not reset**. The avatar remains as it was, preventing the UI from breaking immersion.
5.  **Asset Validation**: Before switching states, the system checks if `assets/maya_{state}.mp4` exists. If the file is missing, it logs a warning and keeps the current avatar.

## Transition Architecture (Fade-In)

To ensure smooth visual transitions between the default avatar and emotional animations:
1.  **Workflow**: Default Avatar (Background) -> Emotional Image (Fade In) -> Emotional Video (Play).
2.  **Implementation**:
    *   The container has the default avatar as a background image.
    *   The video element has `opacity: 0` initially and animates to `1` over 1.5 seconds.
    *   The video element uses the **static emotion image** as its `poster`.
3.  **Result**: The default avatar is visible, then the emotional start-frame fades in smoothly, followed by the video playback.

## Asset Management

Assets are located in the `assets/` directory.

### Naming Convention
For each emotion, you need **two files**:
1.  **Video**: `maya_{emotion}.mp4`
2.  **Poster Image**: `maya_{emotion}.png` OR `maya_{emotion}.jpg`

*Example*:
-   `maya_flustered.mp4`
-   `maya_flustered.png`

### Default Fallback
-   `assets/bartender_avatar.jpg` is the system default.

## Adding New Emotions

1.  **Update Prompt**: Add the new emotion to the list in `src/llm/prompts.py` with an example.
2.  **Update Validation**: Add the string to the `valid_emotions` list in `src/ui/handlers.py`.
3.  **Add Assets**: Drop matching `.mp4` and `.png/.jpg` files into `assets/`.
4.  **Verify**: Use `EMOTION_VERIFICATION.md` to test the trigger.
