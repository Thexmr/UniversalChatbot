# UniversalChatbot 🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Ein **intelligenter Browser-Chat-Agent**, der auf Webseiten Chatfenster erkennt, Nachrichten liest und mit Hilfe von KI (OpenAI GPT) automatisch antworten kann.

## ✨ Funktionen

- 🔍 **Automatische Chat-Erkennung** - Erkennt WhatsApp, Telegram, Discord Web
- 💬 **KI-Antworten** - Nutzt OpenAI GPT für intelligente Antworten
- 🔒 **100% Lokal** - Keine Daten in der Cloud, alles auf deinem PC
- 🛡️ **Sicher** - Whitelist-basiert, nur auf erlaubten Seiten aktiv
- ⚡ **Echtzeit** - Nahezu sofortige Antworten

## 📋 Unterstützte Plattformen

| Plattform | Status | Adapter |
|-----------|--------|---------|
| WhatsApp Web | ✅ Vollständig | Chrome Extension + Python |
| Telegram Web | ✅ Vollständig | Chrome Extension + Python |
| Discord Web | ✅ Vollständig | Chrome Extension + Python |

## 🚀 Schnellstart

### 1. Chrome Extension installieren

```bash
# 1. Repository klonen
git clone https://github.com/Thexmr/UniversalChatbot.git
cd UniversalChatbot

# 2. Chrome Extension aktivieren
# Öffne chrome://extensions/
# Aktiviere "Entwicklermodus"
# Klicke "Entpackte Erweiterung laden"
# Wähle den Ordner "UniversalChatbot/"
```

### 2. Python Backend installieren

**Windows:**
```bash
install.bat
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

### 3. API Key konfigurieren

```bash
# Kopiere die Beispiel-Konfiguration
cp backend/.env.example backend/.env

# Bearbeite backend/.env und füge deinen OpenAI Key hinzu
# OPENAI_API_KEY=sk-...
```

### 4. Starten

```bash
./start.sh  # oder start.bat
```

## 🛠️ Manuelle Installation

### Voraussetzungen

- Python 3.11+
- Chrome/Edge/Chromium Browser
- OpenAI API Key

### Schritt-für-Schritt

1. **Python Dependencies installieren:**
   ```bash
   cd backend/
   pip install -r requirements.txt
   ```

2. **Native Messaging Host registrieren:**
   
   **Windows:**
   ```bash
   python setup_windows.py
   ```
   
   **Linux/Mac:**
   ```bash
   python3 setup_unix.py
   ```

3. **Extension laden:**
   - `chrome://extensions/` öffnen
   - "Entwicklermodus" aktivieren
   - "Entpackte Erweiterung laden"
   - Ordner `UniversalChatbot/` auswählen

4. **Backend starten:**
   ```bash
   cd backend/
   python main.py
   ```

## 🔧 Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER                                  │
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

## 🧪 Tests

```bash
cd backend/
python tests/test_all.py
```

## 📁 Projektstruktur

```
UniversalChatbot/
├── manifest.json          # Chrome Extension Manifest
├── content.js             # Browser-side chat detection
├── background.js          # Extension background service worker  
├── popup.html/js          # Extension popup UI
├── native-messaging.js    # Native host communication
├── adapters/              # Platform-specific configs
│   ├── whatsapp.json
│   ├── telegram.json
│   └── discord.json
├── backend/               # Python backend
│   ├── main.py
│   ├── chatbot/
│   │   ├── native_host.py
│   │   ├── chat_manager.py
│   │   └── llm_client.py
│   └── tests/
├── tests/                 # Frontend tests
└── docs/                  # Documentation
```

## 🔐 Sicherheit

- **API Keys nur lokal** - Nie in GitHub committen
- **Whitelist-Check** - Nur erlaubte Domains
- **Keine Cloud-Daten** - Alles auf deinem PC
- **Native Messaging** - Keine Netzwerk-Ports
- **Benutzer-Kontrolle** - Jederzeit pausierbar

## 🐛 Fehlersuche

### Extension sagt "Native Host not connected"

1. Prüfe ob Python Backend läuft
2. Führe `verify_setup.py` aus
3. Chrome neu starten

### Antworten kommen nicht

1. Prüfe `.env` Datei und API Key
2. Siehe Logs: `backend/logs/chat.log`
3. Prüfe Internetverbindung

## 🤝 Mitwirken

Pull Requests willkommen! Für große Änderungen erstelle bitte zuerst ein Issue.

## 📄 Lizenz

MIT License - Siehe [LICENSE](LICENSE)

## 🙏 Credits

- OpenAI für GPT API
- Chrome Extension Manifest V3
- Python Community

---

**Hinweis:** Dies ist ein Hobby-Projekt. Verwende es verantwortungsvoll und nur auf Plattformen, wo es erlaubt ist.
