# WebSocket Race Condition Fix & Retry Implementation

## Problem
Der User berichtete von häufigen WebSocket-Verbindungsfehlern beim ersten Versuch einen Agenten-Job zu starten. Der Fehler "Connection not ready" trat oft auf, funktionierte aber beim 2. oder 3. Versuch.

## Root Cause Analysis
Das Problem war eine **Race Condition** zwischen:
1. WebSocket-Verbindung wird als "open" erkannt
2. Server ist noch nicht bereit, Nachrichten zu verarbeiten
3. Frontend sendet sofort Nachrichten ohne auf Server-Bereitschaft zu warten

## Implementierte Lösung

### Frontend Verbesserungen (home.tsx)

#### 1. Neue State Variables
```typescript
const [isSocketReady, setIsSocketReady] = useState(false); // Server confirmed ready
const [messageQueue, setMessageQueue] = useState<any[]>([]); // Queue for messages
const [retryAttempt, setRetryAttempt] = useState(0); // Track retry attempts
```

#### 2. Message Queue System
- Nachrichten werden zwischengespeichert wenn Server nicht bereit ist
- Automatische Verarbeitung der Queue wenn Server ready wird
- Queue wird bei Verbindungsabbruch geleert

#### 3. Retry-Logik mit sendMessageWithRetry()
```typescript
const sendMessageWithRetry = async (message: any, maxRetries: number = 3): Promise<boolean>
```
- Bis zu 3 Wiederholungsversuche
- Exponential backoff (500ms, 1000ms delays)
- Fallback zur Message Queue bei Max-Retries

#### 4. Debug-Logging
Alle Logs enthalten das Kennwort **"WEBSOCKET_DEBUG"** für einfache Suche:
- WebSocket-Verbindungsstatus
- Message Queue Länge
- Retry-Versuche
- Server-Readiness-Status

### Backend Verbesserungen (ws_server.py)

#### 1. Erweiterte Debug-Logs
Alle Logs enthalten das Kennwort **"BACKEND_WS_DEBUG"**:
- Verbindungsdetails (IP, Connection ID)
- Message-Verarbeitung
- Agent-Initialisierung
- Workspace-Status

#### 2. Server-Ready-Signale
- `connection_established` Event enthält `server_ready: true`
- `agent_initialized` Event bestätigt Backend-Bereitschaft
- `workspace_info` Response mit `connection_ready: true`

#### 3. Verbesserte Error-Handling
Strukturierte Fehlercodes:
- `QUERY_IN_PROGRESS`: Mehrfache gleichzeitige Queries
- `WORKSPACE_NOT_INITIALIZED`: Workspace-Setup-Fehler
- `WORKSPACE_ERROR`: Allgemeine Workspace-Probleme

#### 4. Bessere workspace_info Behandlung
- Validierung dass Workspace initialisiert ist
- Detaillierte Fehlermeldungen
- Retry-freundliche Responses

## Debugging

### Frontend Console Logs
Suche nach `WEBSOCKET_DEBUG` um alle relevanten Logs zu finden:
```
WEBSOCKET_DEBUG: Starting WebSocket connection process
WEBSOCKET_DEBUG: Server ready signal received, setting isSocketReady=true
WEBSOCKET_DEBUG: Attempting to send message (attempt 1/4)
WEBSOCKET_DEBUG: Processing 2 queued messages
```

### Backend Server Logs
Suche nach `BACKEND_WS_DEBUG` um alle relevanten Logs zu finden:
```
BACKEND_WS_DEBUG: New WebSocket connection attempt from 127.0.0.1, connection_id: 140234567890
BACKEND_WS_DEBUG: Agent initialized for connection 140234567890, sending confirmation
BACKEND_WS_DEBUG: Processing query for connection 140234567890: 'Create a simple...'
```

## Überwachung & Testing

1. **Öffne Browser Console** und suche nach den Debug-Keywords
2. **Prüfe Message Queue**: Logs zeigen Queue-Länge und verarbeitete Nachrichten
3. **Überprüfe Retry-Versuche**: Logs zeigen Anzahl der Versuche
4. **Backend-Logs**: Überprüfe Server-Logs für BACKEND_WS_DEBUG-Nachrichten

## Erwartete Verbesserungen

- **Reduzierte Fehlschläge** beim ersten Versuch
- **Keine verlorenen Nachrichten** durch Message Queue
- **Bessere User Experience** durch automatische Retries
- **Einfachere Fehlerdiagnose** durch detaillierte Logs
- **Stabilere Verbindungen** durch Server-Readiness-Detection

## Fallback-Verhalten

Wenn alle Retry-Versuche fehlschlagen:
1. Nachricht wird in Queue gespeichert
2. User bekommt hilfreiche Fehlermeldung
3. Bei nächster erfolgreicher Verbindung wird Queue verarbeitet
4. Page-Refresh als letzter Ausweg bleibt verfügbar
