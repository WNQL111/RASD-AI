import api from './api';

export const RealtimeConnectionState = {
  DISCONNECTED: 'DISCONNECTED',
  CONNECTING: 'CONNECTING',
  CONNECTED: 'CONNECTED',
  RECONNECTING: 'RECONNECTING',
  FAILED: 'FAILED'
};

class RealtimeClientManager {
  constructor() {
    this.eventSource = null;
    this.connectionState = RealtimeConnectionState.DISCONNECTED;
    this.listeners = new Map(); // eventType -> Set(callbacks)
    this.stateListeners = new Set();
    this.seenEventIds = new Set();
    this.lastEventId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
  }

  connect() {
    if (this.eventSource && this.eventSource.readyState !== EventSource.CLOSED) {
      return;
    }

    this.updateState(
      this.reconnectAttempts > 0 
        ? RealtimeConnectionState.RECONNECTING 
        : RealtimeConnectionState.CONNECTING
    );

    const baseURL = api.defaults.baseURL || `http://${window.location.hostname}:8001/api`;
    let sseUrl = `${baseURL.replace(/\/$/, '')}/alerts/stream`;
    if (this.lastEventId) {
      sseUrl += `?last_event_id=${encodeURIComponent(this.lastEventId)}`;
    }

    try {
      this.eventSource = new EventSource(sseUrl);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateState(RealtimeConnectionState.CONNECTED);
      };

      this.eventSource.onerror = (err) => {
        if (this.eventSource.readyState === EventSource.CLOSED) {
          this.updateState(RealtimeConnectionState.DISCONNECTED);
        } else {
          this.updateState(RealtimeConnectionState.RECONNECTING);
        }
        this.handleReconnect();
      };

      const handleIncomingMessage = (e) => {
        if (e.lastEventId) {
          this.lastEventId = e.lastEventId;
        }
        try {
          const data = JSON.parse(e.data);
          const evId = data.event_id || data.id;

          // Deduplication check
          if (evId) {
            if (this.seenEventIds.has(evId)) {
              return;
            }
            if (this.seenEventIds.size >= 500) {
              const oldest = this.seenEventIds.values().next().value;
              this.seenEventIds.delete(oldest);
            }
            this.seenEventIds.add(evId);
          }

          const evType = data.type || e.type || 'alert';
          this.notifyListeners(evType, data);
          this.notifyListeners('*', data);
        } catch (err) {
          console.error("RealtimeClient: Error parsing event JSON:", err);
        }
      };

      this.eventSource.addEventListener('message', handleIncomingMessage);
      this.eventSource.addEventListener('alert', handleIncomingMessage);
      this.eventSource.addEventListener('progress_update', handleIncomingMessage);
      this.eventSource.addEventListener('analysis_complete', handleIncomingMessage);
      this.eventSource.addEventListener('status_update', handleIncomingMessage);

    } catch (err) {
      console.error("RealtimeClient: Connection initialization error:", err);
      this.updateState(RealtimeConnectionState.FAILED);
    }
  }

  handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.updateState(RealtimeConnectionState.FAILED);
      return;
    }
    this.reconnectAttempts += 1;
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.updateState(RealtimeConnectionState.DISCONNECTED);
  }

  subscribe(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType).add(callback);

    if (this.connectionState === RealtimeConnectionState.DISCONNECTED) {
      this.connect();
    }

    return () => {
      const set = this.listeners.get(eventType);
      if (set) {
        set.delete(callback);
      }
    };
  }

  onStateChange(callback) {
    this.stateListeners.add(callback);
    callback(this.connectionState);
    return () => this.stateListeners.delete(callback);
  }

  updateState(newState) {
    this.connectionState = newState;
    this.stateListeners.forEach(cb => cb(newState));
  }

  notifyListeners(eventType, payload) {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      callbacks.forEach(cb => cb(payload));
    }
  }
}

export const realtimeClient = new RealtimeClientManager();
