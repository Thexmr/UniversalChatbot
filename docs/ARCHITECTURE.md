# System Architecture - UniversalChatbot

## Overview

Ein lokaler Browser-Chat-Agent, der auf Webseiten Chatfenster erkennt, Nachrichten liest und mit Hilfe einer LLM-Antwort generiert.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (Chrome/Firefox)                │
│  ┌──────────────┐         ┌──────────────────────┐       │
│  │   Content    │◄───────►│   Background Service │       │
│  │   Script     │   DOM   │       Worker         │       │
│  └──────────────┘         └──────────┬─────────────┘       │
└──────────────────────────────────────┼─────────────────────┘
                                       │ Native Messaging
┌──────────────────────────────────────┼─────────────────────┐
│              LOKALES SYSTEM            │                     │
│  ┌───────────────────────────────────┴──────────┐         │
│  │         Python Steuerungsdienst              │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │         │
│  │  │Chat      │  │  LLM    │  │  Logger │   │         │
│  │  │Manager   │  │  API    │  │         │   │         │
│  │  └──────────┘  └──────────┘  └──────────┘   │         │
│  └───────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Browser Extension (Chrome/Firefox)

**Content Script**
- Injiziert in Webseiten
- MutationObserver erkennt Chat-Änderungen
- Extrahiert Nachrichten über CSS Selectoren
- Fügt Text in Input-Felder ein

**Background Service Worker**
- Verbindet zu Native Messaging Host
- Verwaltet Extension-Status
- Whitelist-Prüfung

### 2. Python Local Service

**NativeHost**
- JSON über stdin/stdout
- Protokoll-Handling

**ChatManager**
- Session-Verwaltung (UUID)
- Chat-History (letzte 10 Nachrichten)
- Kontext für LLM

**LLMClient**
- OpenAI API Integration
- Prompt-Templates
- Response-Handling

**Logger**
- JSON-Lines Format
- RotatingFileHandler
- INFO/WARNING/ERROR

## Communication Protocol

### Extension → Service

```json
{
  "type": "chat_update",
  "session_id": "uuid-v4",
  "platform": "whatsapp",
  "messages": [
    {"role": "user", "text": "Hallo", "timestamp": "2025-03-26T21:00:00Z"}
  ],
  "requires_response": true
}
```

### Service → Extension

```json
{
  "type": "insert_text",
  "session_id": "uuid-v4",
  "text": "Hallo! Wie kann ich helfen?",
  "auto_send": false
}
```

## Security

- API Keys nur im lokalen Service
- Whitelist für erlaubte Domains
- Native Messaging = keine Netzwerk-Ports
- Lokale Logs nur
- Benutzer kann jederzeit pausieren

## Supported Platforms (MVP)

| Platform | Domain | Status |
|----------|--------|--------|
| WhatsApp | web.whatsapp.com | ✅ Supported |
| Telegram | web.telegram.org | ✅ Supported |
| Discord | discord.com/app | 🚧 Planned |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Extension | JavaScript (ES2020), Manifest V3 |
| Backend | Python 3.11+ |
| API | OpenAI GPT-3.5/4 |
| Data Format | JSON |

---
