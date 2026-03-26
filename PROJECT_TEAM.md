# 🤖 UniversalChatbot - Coding Team

## Projekt: Lokaler Browser-Chat-Agent

**Ziel:** Ein universeller Chatbot, der auf beliebigen Websites Chatfenster erkennt und autonom kommunizieren kann.

---

## Architektur

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

---

## Team Rollen

| Agent | Rolle | Verantwortung | Tech Stack |
|-------|-------|---------------|------------|
| 🏗️ **System Architect** | Lead | Gesamtarchitektur, Schnittstellen | System Design |
| 🔌 **Extension Dev** | Browser | Chrome Extension, Content Scripts | JS, WebExtension API |
| 🐍 **Backend Dev** | Service | Python Service, Native Messaging | Python, FastAPI |
| 🔗 **Integration Dev** | APIs | LLM APIs, Adapters | OpenAI, Gemini |
| 🧪 **QA Engineer** | Testing | Tests, Fehleranalyse | Jest, Pytest |

---

## MVP Scope (Phase 1)

### Kernfunktionen:
1. ✅ Chatfenster Erkennung (CSS Selektoren)
2. ✅ Nachrichten auslesen (MutationObserver)
3. ✅ Text eingeben & senden
4. ✅ LLM API Anbindung (OpenAI)
5. ✅ Einfache Config (JSON Adapter)

### Unterstützte Plattformen (Phase 1):
- WhatsApp Web
- Telegram Web
- Discord Web

---

## Komponenten

### 1. Browser Extension
```
extension/
├── manifest.json
├── background.js           # Service Worker
├── content.js              # Chat-Erkennung
├── content-styles.css      # Markierungen
├── adapters/
│   ├── whatsapp.json     # CSS Selektoren
│   ├── telegram.json
│   └── discord.json
└── icons/
```

### 2. Python Service
```
backend/
├── main.py                 # Entry point
├── native_messaging.py     # Host Kommunikation
├── chat_manager.py         # Kontext & History
├── llm_client.py           # API Integration
├── adapters/
│   └── base_adapter.py
├── config/
│   └── settings.yaml
└── logs/
    └── chat.log
```

---

## Native Messaging Protocol

```json
// Extension → Backend
{
  "type": "chat_update",
  "session_id": "uuid-v4",
  "platform": "whatsapp",
  "messages": [
    {"sender": "User", "text": "Hallo", "timestamp": "..."}
  ],
  "requires_response": true
}

// Backend → Extension
{
  "type": "insert_text",
  "session_id": "uuid-v4",
  "text": "Automatisierte Antwort...",
  "auto_send": false
}
```

---

## Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Extension | Chrome Extension Manifest V3 |
| Backend | Python 3.11+ |
| Web Framework | FastAPI |
| LLM APIs | OpenAI GPT-4, Gemini |
| Datenformat | JSON |
| Logging | JSON-Lines |

---

## Sicherheit

- ✅ API Keys nur in lokalem Service
- ✅ Whitelist für erlaubte Domains
- ✅ Kein Remote-Code
- ✅ Lokale Logs nur
- ✅ Benutzer kann jederzeit pausieren

---

*Letztes Update: 28.03.2026*
**Status: Phase 1 - MVP Development**
