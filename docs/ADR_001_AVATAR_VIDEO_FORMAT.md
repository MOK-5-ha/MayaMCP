# ADR 001: Avatar Video Format (MP4 vs GIF)

**Status**: Accepted  
**Date**: 2025-12-16  
**Context**: Generation of animated scenes for Maya's emotional states using Google Whisk.

## Decision
We have decided to use **.mp4** format for all avatar animations instead of .gif.

## Rationale

### 1. Color Depth & Quality
*   **GIF**: Limited to a palette of 256 colors. This results in visible "banding," dithered speckles, and loss of detail, especially when converting from high-quality AI-generated images.
*   **MP4**: Supports millions of colors (24-bit+). This ensures the animated video is visually identical to the original high-resolution source image (consistent with `bartender_avatar.jpg`).

### 2. Performance & Latency
*   **File Size**: 720p GIFs are inefficiently compressed and can be massive (tens of MBs), leading to slow load times and bandwidth waste. MP4 codecs (H.264) are highly optimized, resulting in significantly smaller files for superior quality.
*   **Rendering**: MP4 playback is hardware-accelerated by modern browsers. Large GIFs can be CPU-intensive to decode, causing UI stuttering.

### 3. Implementation
*   **Browser Support**: Modern browsers universally support `<video autoplay loop muted playsinline>`, which is the standard pattern for "gif-like" behavior without the downsides of the GIF format.
*   **UI Integration**: Our `tab_overlay.py` component is already configured to render `.mp4` files using the HTML5 video tag.

## Consequences
*   **Assets**: All generated assets from Google Whisk should be downloaded as MP4.
*   **Code**: No changes required (UI already supports MP4).
