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
  private currentSessionId: string | null = null;

  public setSessionId(sessionId: string): void {
    this.currentSessionId = sessionId;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('maya_session_id', sessionId);
    }
  }

  public getSessionId(): string | null {
    if (!this.currentSessionId && typeof localStorage !== 'undefined') {
      this.currentSessionId = localStorage.getItem('maya_session_id');
    }
    return this.currentSessionId;
  }

  public connectAndStream(
    message: string,
    onEvent: (event: StreamEvent) => void,
    onError: (error: any) => void,
    sessionId?: string
  ): void {
    if (this.eventSource) {
      this.eventSource.close();
    }

    const activeSessionId = sessionId || this.getSessionId() || '';
    const encodedMessage = encodeURIComponent(message);
    let streamUrl = `/api/chat/stream?message=${encodedMessage}`;
    if (activeSessionId) {
      streamUrl += `&session_id=${encodeURIComponent(activeSessionId)}`;
    }

    this.eventSource = new EventSource(streamUrl);

    this.eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        if (data.type === 'session' && data.session_id) {
          this.setSessionId(data.session_id);
        }
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
