import { SSEClient } from './SSEClient';

export interface ChatControllerCallbacks {
  /** Called when a message is accepted for sending (e.g. reset dialogue). */
  onSend: (text: string) => void;
  /** Called with each streamed text delta for progressive dialogue rendering. */
  onDelta: (delta: string) => void;
  /** Called once the stream completes with Maya's full response text. */
  onComplete: (fullResponse: string) => void;
  /** Called when the stream errors out before completing. */
  onError: (message: string) => void;
}

/**
 * Owns the SSE chat lifecycle for the bar scene: send a user message,
 * stream Maya's reply, and hand completion events to the HUD. Chip polling
 * is orchestrated by the HUD after onComplete fires — never inside the
 * stream, because chips are generated asynchronously after the stream ends.
 */
export class ChatController {
  private client = new SSEClient();
  private hud: ChatControllerCallbacks | null = null;
  private busy = false;

  /** Bind the HUD callbacks (called by HUDOverlayScene on scene create). */
  public bindHUD(callbacks: ChatControllerCallbacks): void {
    this.hud = callbacks;
  }

  public isBusy(): boolean {
    return this.busy;
  }

  public send(text: string): void {
    const trimmed = text.trim();
    if (!trimmed || this.busy || !this.hud) {
      return;
    }
    this.busy = true;
    this.hud.onSend(trimmed);
    this.client.connectAndStream(
      trimmed,
      (event) => this.handleEvent(event),
      () => {
        this.busy = false;
        this.hud?.onError("I'm sorry — the connection to the bar was interrupted. Please try again.");
      },
    );
  }

  public disconnect(): void {
    this.client.disconnect();
    this.busy = false;
  }

  private handleEvent(event: {
    type: string;
    content?: string;
    full_response?: string;
  }): void {
    if (!this.hud) return;
    if (event.type === 'text_chunk' && event.content) {
      this.hud.onDelta(event.content);
      return;
    }
    if (event.type === 'complete') {
      this.busy = false;
      this.hud.onComplete(event.full_response ?? event.content ?? '');
      return;
    }
    if (event.type === 'error') {
      this.busy = false;
      this.hud.onError(event.content ?? 'Unexpected error while streaming.');
    }
  }
}
