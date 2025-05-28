/**
 * WebSocket Connection Monitor
 * 
 * Utility for monitoring WebSocket connection health and providing debugging information.
 */

export interface WebSocketHealthInfo {
  isConnected: boolean;
  readyState: number;
  readyStateText: string;
  lastError?: string;
  connectionAttempts: number;
  lastConnectedAt?: Date;
  lastDisconnectedAt?: Date;
}

export class WebSocketMonitor {
  private connectionAttempts = 0;
  private lastConnectedAt?: Date;
  private lastDisconnectedAt?: Date;
  private lastError?: string;

  getReadyStateText(readyState: number): string {
    switch (readyState) {
      case WebSocket.CONNECTING:
        return "CONNECTING";
      case WebSocket.OPEN:
        return "OPEN";
      case WebSocket.CLOSING:
        return "CLOSING";
      case WebSocket.CLOSED:
        return "CLOSED";
      default:
        return "UNKNOWN";
    }
  }

  getCloseCodeText(code: number): string {
    switch (code) {
      case 1000:
        return "Normal closure";
      case 1001:
        return "Going away";
      case 1002:
        return "Protocol error";
      case 1003:
        return "Unsupported data";
      case 1006:
        return "Abnormal closure";
      case 1007:
        return "Invalid frame payload data";
      case 1008:
        return "Policy violation";
      case 1009:
        return "Message too big";
      case 1010:
        return "Mandatory extension";
      case 1011:
        return "Internal server error";
      case 1013:
        return "Service overloaded";
      case 1015:
        return "TLS handshake";
      default:
        return `Unknown code: ${code}`;
    }
  }

  onConnectionAttempt(): void {
    this.connectionAttempts++;
  }

  onConnected(): void {
    this.lastConnectedAt = new Date();
  }

  onDisconnected(): void {
    this.lastDisconnectedAt = new Date();
  }

  onError(error: string): void {
    this.lastError = error;
  }

  getHealthInfo(socket: WebSocket | null): WebSocketHealthInfo {
    return {
      isConnected: socket?.readyState === WebSocket.OPEN,
      readyState: socket?.readyState ?? -1,
      readyStateText: socket ? this.getReadyStateText(socket.readyState) : "NO_SOCKET",
      lastError: this.lastError,
      connectionAttempts: this.connectionAttempts,
      lastConnectedAt: this.lastConnectedAt,
      lastDisconnectedAt: this.lastDisconnectedAt,
    };
  }

  logHealthInfo(socket: WebSocket | null, context?: string): void {
    const health = this.getHealthInfo(socket);
    const prefix = context ? `[${context}] ` : "";
    
    console.group(`${prefix}🔍 WebSocket Health Info`);
    console.log("Is Connected:", health.isConnected);
    console.log("Ready State:", `${health.readyState} (${health.readyStateText})`);
    console.log("Connection Attempts:", health.connectionAttempts);
    console.log("Last Connected:", health.lastConnectedAt?.toISOString() || "Never");
    console.log("Last Disconnected:", health.lastDisconnectedAt?.toISOString() || "Never");
    console.log("Last Error:", health.lastError || "None");
    console.groupEnd();
  }

  reset(): void {
    this.connectionAttempts = 0;
    this.lastConnectedAt = undefined;
    this.lastDisconnectedAt = undefined;
    this.lastError = undefined;
  }
}

// Export a singleton instance
export const wsMonitor = new WebSocketMonitor(); 