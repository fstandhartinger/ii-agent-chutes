# Native Tool Calling für Chutes LLMs

Diese Implementierung fügt native Tool-Calling-Unterstützung für Chutes LLMs hinzu, inspiriert vom Squad-API-Projekt. Sie bietet eine Alternative zum bestehenden JSON-Workaround-Ansatz.

## Problem

Bisher verwendete das System einen JSON-Workaround für Tool-Calls bei Chutes LLMs:
- Das LLM wurde instruiert, Tool-Calls als JSON-Blöcke in der Antwort zu formatieren
- Diese JSON-Blöcke wurden dann geparst und in interne ToolCall-Objekte umgewandelt
- Dies war fehleranfällig und weniger elegant als native Tool-Calling

## Lösung

Die neue Implementierung bietet zwei Modi:

### 1. JSON-Workaround-Modus (Standard)
- **Aktivierung**: `use_native_tool_calling=False` (Standard)
- **Funktionsweise**: Wie bisher - LLM gibt JSON-formatierte Tool-Calls zurück
- **Kompatibilität**: Vollständig rückwärtskompatibel

### 2. Native Tool-Calling-Modus (Neu)
- **Aktivierung**: `use_native_tool_calling=True`
- **Funktionsweise**: Verwendet OpenAI-kompatible Tool-Calling-API
- **Vorteile**: Sauberer, weniger fehleranfällig, folgt dem Squad-Vorbild

## Implementierung

### Backend-Änderungen

#### ChutesOpenAIClient
```python
class ChutesOpenAIClient(LLMClient):
    def __init__(self, use_native_tool_calling=False, ...):
        self.use_native_tool_calling = use_native_tool_calling
```

**Tool-Verarbeitung:**
- **Native Modus**: Tools werden als OpenAI-kompatible `tools` Parameter gesendet
- **JSON Modus**: Tools werden als System-Prompt-Instruktionen hinzugefügt

**Antwort-Verarbeitung:**
- **Native Modus**: Verarbeitet `message.tool_calls` direkt
- **JSON Modus**: Parst JSON-Blöcke aus `message.content`

#### WebSocket-Server
```python
use_native_tool_calling = websocket.query_params.get("use_native_tool_calling", "false").lower() == "true"
client = get_client(
    "chutes-openai",
    use_native_tool_calling=use_native_tool_calling,
    ...
)
```

### Frontend-Änderungen

#### Toggle-Komponente
```tsx
const [useNativeToolCalling, setUseNativeToolCalling] = useState(false);

// WebSocket URL
if (useNativeToolCalling) {
  wsUrl += `&use_native_tool_calling=true`;
}
```

**UI-Element:**
- Toggle-Schalter im Header (nur sichtbar wenn nicht im Chat-Modus)
- Zeigt aktuellen Status an: "Native Tool Calling" vs "JSON Workaround"
- Tooltip erklärt die Modi

## Verwendung

### 1. Über die Web-UI
1. Öffnen Sie die Anwendung
2. Klicken Sie auf den "Native Tool Calling" Toggle im Header
3. Der Toggle wird blau, wenn aktiviert
4. Starten Sie eine neue Konversation

### 2. Über WebSocket-Parameter
```javascript
const wsUrl = `ws://localhost:8000/ws?use_chutes=true&use_native_tool_calling=true`;
```

### 3. Direkt im Code
```python
client = ChutesOpenAIClient(
    model_name="deepseek-ai/DeepSeek-V3-0324",
    use_native_tool_calling=True  # Aktiviert nativen Modus
)
```

## Testen

### Automatisierte Tests
```bash
python test_native_tool_calling.py
```

**Test-Szenarien:**
1. JSON-Workaround-Modus mit Tool-Calls
2. Native Tool-Calling-Modus mit Tool-Calls  
3. Multi-Turn-Konversation mit Tool-Ergebnissen

### Manuelle Tests
1. **JSON-Modus testen:**
   - Toggle ausgeschaltet lassen
   - Frage stellen: "Was ist 25 * 37?"
   - Logs prüfen: `[CHUTES] Implementing JSON workaround`

2. **Native Modus testen:**
   - Toggle einschalten
   - Frage stellen: "Was ist 25 * 37?"
   - Logs prüfen: `[CHUTES] Using native tool calling`

## Vergleich der Modi

| Aspekt | JSON-Workaround | Native Tool-Calling |
|--------|-----------------|-------------------|
| **Kompatibilität** | ✅ Bewährt | ⚠️ Neu, experimentell |
| **Fehleranfälligkeit** | ❌ JSON-Parsing-Fehler | ✅ Robuster |
| **Performance** | ❌ Zusätzliche Parsing-Schritte | ✅ Direkter |
| **Debugging** | ❌ Komplexere Logs | ✅ Klarere Logs |
| **Squad-Kompatibilität** | ❌ Eigener Ansatz | ✅ Folgt Squad-Vorbild |

## Logs und Debugging

### JSON-Workaround-Modus
```
[CHUTES] JSON WORKAROUND MODE (default)
[CHUTES] Implementing JSON workaround for 3 tools
[CHUTES] Found 1 potential JSON tool calls in content
[CHUTES] Extracted tool call from JSON: {'name': 'calculate', ...}
```

### Native Tool-Calling-Modus
```
[CHUTES] NATIVE TOOL CALLING MODE ENABLED
[CHUTES] Using native tool calling for 3 tools
[CHUTES] Added 3 tools to payload for native calling
[CHUTES] Processing 1 native tool calls
```

## Bekannte Einschränkungen

1. **Experimenteller Status**: Native Modus ist neu und weniger getestet
2. **Chutes-Kompatibilität**: Abhängig von Chutes' OpenAI-API-Kompatibilität
3. **Fallback**: Bei Fehlern im nativen Modus kein automatischer Fallback zum JSON-Modus

## Zukünftige Verbesserungen

1. **Automatischer Fallback**: Bei Fehlern im nativen Modus automatisch zum JSON-Modus wechseln
2. **Persistente Einstellungen**: Toggle-Status in localStorage speichern
3. **Modell-spezifische Defaults**: Verschiedene Modi für verschiedene Modelle
4. **Performance-Metriken**: Vergleich der Modi in Bezug auf Geschwindigkeit und Zuverlässigkeit

## Troubleshooting

### Problem: Native Modus funktioniert nicht
**Lösung**: 
1. Prüfen Sie die Logs auf `[CHUTES] NATIVE TOOL CALLING MODE ENABLED`
2. Wechseln Sie zurück zum JSON-Modus als Fallback
3. Prüfen Sie die Chutes-API-Kompatibilität

### Problem: Toggle wird nicht angezeigt
**Lösung**:
1. Stellen Sie sicher, dass Sie nicht im Chat-Modus sind
2. Aktualisieren Sie die Seite
3. Prüfen Sie die Browser-Konsole auf Fehler

### Problem: WebSocket-Verbindung schlägt fehl
**Lösung**:
1. Prüfen Sie die WebSocket-URL in den Browser-Entwicklertools
2. Stellen Sie sicher, dass der Parameter korrekt übertragen wird
3. Prüfen Sie die Server-Logs auf Fehler

## Fazit

Die native Tool-Calling-Implementierung bietet eine moderne, robuste Alternative zum JSON-Workaround. Sie folgt dem bewährten Squad-Vorbild und bereitet das System auf zukünftige Verbesserungen vor. Der Toggle ermöglicht es Benutzern, zwischen den Modi zu wechseln und die beste Option für ihren Anwendungsfall zu wählen. 