# Pro Mode Admin Guide - VERTRAULICH

## 🔐 Authentifizierungsmechanismus

### Funktionsweise
Das Pro-System verwendet einen **Prime-Number-basierten Validierungsmechanismus**:

1. **Geheimer Prime**: Eine große Primzahl (aktuell: `1299827`) wird als Basis verwendet
2. **Key-Generierung**: Pro Keys sind 8-stellige Hex-Werte, die Vielfache dieser Primzahl darstellen
3. **Validierung**: Ein Key ist gültig, wenn `parseInt(key, 16) % PRO_PRIME === 0`
4. **Sicherheit**: Ohne Kenntnis der Primzahl können keine gültigen Keys generiert werden

### 🔑 Sichere Primzahl-Speicherung

**Ort**: Render.com Environment Variables
- **Backend**: `PRO_PRIME=1299827`
- **Frontend**: `NEXT_PUBLIC_PRO_PRIME=1299827`

**Zugriff auf Render.com**:
1. Login bei render.com
2. Backend Service → Environment → Environment Variables
3. Frontend Service → Environment → Environment Variables

**WICHTIG**: Diese Primzahl NIEMALS in Code committen oder öffentlich teilen!

## 🎯 Pro Key Generierung

### Lokale Generierung (für Testing)
```bash
# Environment Variable setzen
export PRO_PRIME=1299827
export NEXT_PUBLIC_PRO_PRIME=1299827

# Key generieren
python generate_pro_key.py
```

### Produktions-Generierung
```bash
# Auf Server mit gesetzten Environment Variables
python generate_pro_key.py
```

### Beispiel-Output
```
Generated Pro Key: 13C4A2B3
Example URL: http://localhost:3000/?pro_user_key=13C4A2B3
```

### URL für Kunden
```
https://your-domain.com/?pro_user_key=XXXXXXXX
```

## ⚠️ Monitoring & Limits

### Aktuelle Limits
- **Monatslimit**: 1000 Sonnet 4 Requests pro Pro Key
- **Warnschwelle**: 300 Requests (30% des Limits)
- **Fallback**: Automatischer Wechsel zu DeepSeek V3 nach Limit

### Log-Monitoring
**Warnung bei 300 Requests**:
```
🚨 WARNING: Pro user XXXXXXXX has reached 300 Sonnet 4 requests in 2024-01!
🚨 ALERT: Monitor this user closely - approaching monthly limit of 1000
```

**Kritisch bei 1000 Requests**:
```
🔴 CRITICAL: Pro user XXXXXXXX has exceeded monthly limit (1000) in 2024-01
🔴 FALLBACK: Switching to DeepSeek V3 for this user
```

**Fallback-Aktivierung**:
```
🔄 FALLBACK: Switching from Sonnet 4 to DeepSeek V3 for Pro user XXXXXXXX
```

### Automatischer Fallback
- Bei 1000+ Requests: Automatischer Wechsel zu DeepSeek V3
- Transparent für User (keine UI-Änderung)
- Logs zeigen Fallback-Aktivierung

## 📊 Datenbank-Statistiken

### Grundlegende Statistiken

#### Anzahl Pro-User
```sql
SELECT COUNT(DISTINCT pro_key) as total_pro_users 
FROM pro_usage;
```

#### Gesamte Sonnet 4 Requests
```sql
SELECT SUM(sonnet_requests) as total_sonnet_requests 
FROM pro_usage;
```

#### Aktuelle Monats-Statistiken
```sql
SELECT 
    COUNT(DISTINCT pro_key) as active_pro_users,
    SUM(sonnet_requests) as total_requests,
    AVG(sonnet_requests) as avg_requests_per_user,
    MAX(sonnet_requests) as max_requests_single_user
FROM pro_usage 
WHERE month_year = strftime('%Y-%m', 'now');
```

### Detaillierte Pro-User Analyse

#### Top 10 Pro-User nach Nutzung
```sql
SELECT 
    pro_key,
    month_year,
    sonnet_requests,
    ROUND((sonnet_requests * 100.0 / 1000), 1) as usage_percentage
FROM pro_usage 
WHERE month_year = strftime('%Y-%m', 'now')
ORDER BY sonnet_requests DESC 
LIMIT 10;
```

#### User über Warnschwelle (300+ Requests)
```sql
SELECT 
    pro_key,
    month_year,
    sonnet_requests,
    CASE 
        WHEN sonnet_requests >= 1000 THEN '🔴 LIMIT REACHED'
        WHEN sonnet_requests >= 300 THEN '🚨 WARNING ZONE'
        ELSE '✅ NORMAL'
    END as status
FROM pro_usage 
WHERE sonnet_requests >= 300
ORDER BY sonnet_requests DESC;
```

#### Komplette Pro-User Liste (aktueller Monat)
```sql
SELECT 
    pro_key,
    sonnet_requests,
    (1000 - sonnet_requests) as remaining_requests,
    ROUND((sonnet_requests * 100.0 / 1000), 1) as usage_percentage,
    updated_at
FROM pro_usage 
WHERE month_year = strftime('%Y-%m', 'now')
ORDER BY sonnet_requests DESC;
```

### Historische Analysen

#### Monatliche Trends
```sql
SELECT 
    month_year,
    COUNT(DISTINCT pro_key) as unique_users,
    SUM(sonnet_requests) as total_requests,
    AVG(sonnet_requests) as avg_per_user
FROM pro_usage 
GROUP BY month_year 
ORDER BY month_year DESC;
```

#### User-Retention (wiederkehrende User)
```sql
SELECT 
    pro_key,
    COUNT(DISTINCT month_year) as active_months,
    SUM(sonnet_requests) as total_lifetime_requests
FROM pro_usage 
GROUP BY pro_key 
HAVING active_months > 1
ORDER BY total_lifetime_requests DESC;
```

### Monitoring-Queries für Alerts

#### User nahe dem Limit (80%+)
```sql
SELECT 
    pro_key,
    sonnet_requests,
    ROUND((sonnet_requests * 100.0 / 1000), 1) as usage_percentage
FROM pro_usage 
WHERE month_year = strftime('%Y-%m', 'now')
AND sonnet_requests >= 800
ORDER BY sonnet_requests DESC;
```

#### Verdächtige Aktivität (sehr hohe Nutzung)
```sql
SELECT 
    pro_key,
    sonnet_requests,
    updated_at,
    CASE 
        WHEN sonnet_requests > 500 THEN '🔍 HIGH USAGE'
        WHEN sonnet_requests > 300 THEN '⚠️ MONITOR'
        ELSE '✅ NORMAL'
    END as alert_level
FROM pro_usage 
WHERE month_year = strftime('%Y-%m', 'now')
AND sonnet_requests > 300
ORDER BY sonnet_requests DESC;
```

## 🔧 Praktische Admin-Befehle

### Datenbank-Zugriff
```bash
# SQLite Datenbank öffnen
sqlite3 /var/data/events.db

# Oder lokal
sqlite3 events.db
```

### Schnelle Checks
```bash
# Aktuelle Pro-User Anzahl
echo "SELECT COUNT(DISTINCT pro_key) FROM pro_usage;" | sqlite3 events.db

# User über Warnschwelle
echo "SELECT pro_key, sonnet_requests FROM pro_usage WHERE sonnet_requests >= 300 AND month_year = strftime('%Y-%m', 'now');" | sqlite3 events.db
```

### Log-Monitoring Setup
```bash
# Tail logs für Warnungen
tail -f /var/log/app.log | grep -E "(WARNING|CRITICAL|FALLBACK)"

# Oder mit journalctl (systemd)
journalctl -u your-app-service -f | grep -E "(WARNING|CRITICAL|FALLBACK)"
```

## 🚨 Notfall-Prozeduren

### User temporär sperren
```sql
-- Setze Usage auf Maximum (1000+) um Fallback zu erzwingen
UPDATE pro_usage 
SET sonnet_requests = 1001 
WHERE pro_key = 'XXXXXXXX' 
AND month_year = strftime('%Y-%m', 'now');
```

### User-Limit erhöhen (Ausnahme)
```sql
-- Reduziere Usage für Ausnahme-User
UPDATE pro_usage 
SET sonnet_requests = 0 
WHERE pro_key = 'XXXXXXXX' 
AND month_year = strftime('%Y-%m', 'now');
```

### Neue Primzahl setzen (alle Keys invalidieren)
1. Render.com → Environment Variables
2. `PRO_PRIME` und `NEXT_PUBLIC_PRO_PRIME` ändern
3. Services neu starten
4. Neue Keys für alle User generieren

## 📈 Business Metriken

### Revenue Tracking
```sql
-- Annahme: $20/Monat pro Pro-User
SELECT 
    month_year,
    COUNT(DISTINCT pro_key) as paying_users,
    (COUNT(DISTINCT pro_key) * 20) as estimated_revenue_usd
FROM pro_usage 
GROUP BY month_year 
ORDER BY month_year DESC;
```

### Churn Analysis
```sql
-- User die letzten Monat aktiv waren, aber diesen Monat nicht
SELECT DISTINCT p1.pro_key
FROM pro_usage p1
LEFT JOIN pro_usage p2 ON p1.pro_key = p2.pro_key 
    AND p2.month_year = strftime('%Y-%m', 'now')
WHERE p1.month_year = strftime('%Y-%m', 'now', '-1 month')
AND p2.pro_key IS NULL;
```

---

**WICHTIG**: Diese Datei enthält sensible Informationen. Sicher aufbewahren und nicht öffentlich teilen! 