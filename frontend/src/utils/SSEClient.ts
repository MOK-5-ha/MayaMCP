export interface StreamEvent {
  type: string;
  content?: string;
  text_chunk?: string;
  viseme?: string;
  session_id?: string;
  audio_base64?: string;
}

export class SSEClient {
  private eventSource: EventSource | null = null;

  public connectAndStream(
    message: string,
    onEvent: (event: StreamEvent) => void,
    onError: (error: any) => void
  ): void {
    if (this.eventSource) {
      this.eventSource.close();
    }

    const encodedMessage = encodeURIComponent(message);
    const streamUrl = `/api/chat/stream?message=${encodedMessage}`;

    this.eventSource = new EventSource(streamUrl);

    this.eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        onEvent(data);

        if (data.type === 'complete' || data.type === 'error') {
          this.disconnect();
        }
      } catch (err) {
        console.error('[SSEClient] Error parsing stream event:', err);
      }
    };

    this.eventSource.onerror = (err: Event) => {
      console.warn('[SSEClient] EventSource connection error:', err);
      onError(err);
      this.disconnect();
    };
  }

  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
