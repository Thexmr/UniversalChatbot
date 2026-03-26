# UniversalChatbot Test Suite

This directory contains test pages and utilities for the UniversalChatbot extension.

## Test Pages

### WhatsApp Mock (`test_pages/whatsapp_mock.html`)
A mock WhatsApp Web interface for testing the WhatsApp adapter.

**Features:**
- Simulates WhatsApp Web DOM structure with `data-testid` attributes
- Supports message sending and receiving
- Auto-generates test messages every 10 seconds
- Includes test controls panel

**Usage:**
1. Open `test_pages/whatsapp_mock.html` in Chrome
2. Load the UniversalChatbot extension
3. Verify the extension detects the chat

---

### Discord Mock (`test_pages/discord_mock.html`)
A mock Discord Web interface for testing the Discord adapter.

**Features:**
- Simulates Discord's React-based DOM structure
- Uses dynamic CSS class names (Discord-style)
- Tests `[class*='name']` selector strategy
- Includes typing indicator simulation
- Auto-generates test messages every 15 seconds

**Usage:**
1. Open `test_pages/discord_mock.html` in Chrome
2. Load the UniversalChatbot extension
3. Verify Discord adapter loads correctly
4. Test message extraction and sending

---

## To Run Tests

1. Open Chrome with the UniversalChatbot extension loaded
2. Navigate to `chrome://extensions/` → Enable Developer Mode → Load Unpacked
3. Open one of the mock HTML files (`file://` or via local server)
4. Check the browser console for `[UCB]` logs
5. Test message sending/extraction

## Expected Behavior

When loading a mock page, you should see:

```
[UCB] Loaded adapter: WhatsApp Web/Telegram Web/Discord
[UCB] Starting DOM observer
[UCB] Chat window opened
[UCB] New message: {...}
```

## Adding New Test Pages

1. Create a new HTML file in `test_pages/`
2. Add selectors matching your target platform
3. Include the test controls panel for manual testing
4. Update this README
