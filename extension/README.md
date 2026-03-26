# Universal Chatbot Chrome Extension

Chrome Extension for connecting web chat platforms (WhatsApp, Telegram) to AI chatbot systems.

## Features

- **Chat Window Detection**: Automatically detects when chat windows are opened/closed
- **Message Extraction**: Captures incoming messages from supported platforms
- **Text Input**: Sends responses back to the chat
- **Native Messaging**: Connects to native host application for AI processing

## Supported Platforms

- WhatsApp Web (`web.whatsapp.com`)
- Telegram Web (`web.telegram.org`)

## Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` folder

## Project Structure

```
extension/
├── manifest.json          # Chrome Extension Manifest V3
├── background.js          # Service Worker - Native Messaging Host
├── content.js             # Injected script - DOM observer + message extraction
├── content-styles.css     # Content script styles
├── popup.html             # Extension popup UI
├── popup.js               # Popup script
├── native-messaging.js    # Native Messaging utilities
├── adapters/              # Platform adapters
│   ├── whatsapp.json
│   └── telegram.json
└── icons/                 # Extension icons
    └── icon128.svg
```

## Architecture

```
┌─────────────┐      Native Messaging      ┌─────────────────┐
│   Chrome    │        <──────────>        │  Native Host    │
│  Extension  │                              │  Application    │
└──────┬──────┘                              └─────────────────┘
       │
       │ Content Script
       ↓
┌─────────────────┐
│  WhatsApp Web   │
│  Telegram Web   │
└─────────────────┘
```

## Permissions

- `activeTab`: Access to currently active tab
- `scripting`: Inject content scripts
- `storage`: Save user preferences
- `nativeMessaging`: Communicate with native application

## Native Messaging Host

The extension expects a native host with ID: `com.universalchatbot.bridge`

### Manifest Location

- **Windows**: `HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.universalchatbot.bridge`
- **macOS**: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.universalchatbot.bridge.json`
- **Linux**: `~/.config/google-chrome/NativeMessagingHosts/com.universalchatbot.bridge.json`

## Adapter System

Platform adapters use JSON configuration files defining CSS selectors:

```json
{
  "domain": "web.whatsapp.com",
  "selectors": {
    "chat_container": "[data-testid='chat-list']",
    "messages": "[data-testid='msg-container']",
    "message_text": ".selectable-text",
    "input": "[data-testid='conversation-compose-box-input']",
    "send_button": "[data-testid='send']"
  }
}
```

## License

MIT
