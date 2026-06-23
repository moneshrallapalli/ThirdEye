/**
 * WebSocket service for real-time communication
 */
import { WebSocketMessage, Alert, LiveFeedUpdate, AnalysisUpdate } from '../types';

const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

type MessageHandler = (message: WebSocketMessage) => void;
type LiveFeedHandler = (update: LiveFeedUpdate) => void;
type AnalysisHandler = (update: AnalysisUpdate) => void;
type AlertHandler = (alert: Alert) => void;

class WebSocketService {
  private sockets: Map<string, WebSocket> = new Map();
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  connect(endpoint: string, onMessage?: MessageHandler): void {
    if (this.sockets.has(endpoint)) {
      console.log(`WebSocket already connected to ${endpoint}`);
      return;
    }

    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token');
    const wsUrl = token ? `${WS_BASE_URL}${endpoint}?token=${token}` : `${WS_BASE_URL}${endpoint}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`WebSocket connected to ${endpoint}`);
      this.reconnectAttempts.set(endpoint, 0);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        // Call registered handlers
        const handlers = this.handlers.get(endpoint);
        if (handlers) {
          handlers.forEach(handler => handler(message));
        }

        // Call specific handler if provided
        if (onMessage) {
          onMessage(message);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error on ${endpoint}:`, error);
    };

    ws.onclose = () => {
      console.log(`WebSocket disconnected from ${endpoint}`);
      this.sockets.delete(endpoint);

      // Attempt reconnection
      this.attemptReconnect(endpoint, onMessage);
    };

    this.sockets.set(endpoint, ws);
  }

  private attemptReconnect(endpoint: string, onMessage?: MessageHandler): void {
    const attempts = this.reconnectAttempts.get(endpoint) || 0;

    if (attempts < this.maxReconnectAttempts) {
      console.log(`Attempting to reconnect to ${endpoint} (${attempts + 1}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.reconnectAttempts.set(endpoint, attempts + 1);
        this.connect(endpoint, onMessage);
      }, this.reconnectDelay);
    } else {
      console.error(`Max reconnection attempts reached for ${endpoint}`);
    }
  }

  send(endpoint: string, data: any): void {
    const ws = this.sockets.get(endpoint);

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    } else {
      console.error(`WebSocket not connected to ${endpoint}`);
    }
  }

  addHandler(endpoint: string, handler: MessageHandler): void {
    if (!this.handlers.has(endpoint)) {
      this.handlers.set(endpoint, new Set());
    }
    this.handlers.get(endpoint)!.add(handler);
  }

  removeHandler(endpoint: string, handler: MessageHandler): void {
    const handlers = this.handlers.get(endpoint);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  disconnect(endpoint: string): void {
    const ws = this.sockets.get(endpoint);

    if (ws) {
      ws.close();
      this.sockets.delete(endpoint);
      this.handlers.delete(endpoint);
    }
  }

  disconnectAll(): void {
    this.sockets.forEach((ws, endpoint) => {
      this.disconnect(endpoint);
    });
  }

  // Convenience methods for specific endpoints
  connectLiveFeed(handler: LiveFeedHandler): void {
    this.connect('/ws/live-feed', (message) => {
      if (message.type === 'live_feed_update') {
        handler(message as LiveFeedUpdate);
      }
    });
  }

  connectAlerts(handler: AlertHandler): void {
    this.connect('/ws/alerts', (message) => {
      if (message.type === 'alert' && message.alert) {
        handler(message.alert);
      }
    });
  }

  connectAnalysis(handler: AnalysisHandler): void {
    this.connect('/ws/analysis', (message) => {
      if (message.type === 'analysis_update') {
        handler(message as AnalysisUpdate);
      }
    });
  }

  connectSystem(handler: MessageHandler): void {
    this.connect('/ws/system', handler);
  }
}

export const wsService = new WebSocketService();
export default wsService;
