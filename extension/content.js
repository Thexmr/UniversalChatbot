// Content Script - runs on supported chat platforms
// Detects chat windows, extracts messages, handles message sending

(function() {
  'use strict';

  const PLATFORM_ADAPTERS = {
    'web.whatsapp.com': 'whatsapp',
    'web.telegram.org': 'telegram'
  };

  let currentPlatform = null;
  let adapterConfig = null;
  let observer = null;
  let chatObserver = null;
  let isEnabled = false;
  let lastMessages = new Set();

  // Get the adapter name based on current domain
  function getPlatformAdapter() {
    const hostname = window.location.hostname;
    return PLATFORM_ADAPTERS[hostname] || null;
  }

  // Initialize the content script
  async function init() {
    currentPlatform = getPlatformAdapter();
    if (!currentPlatform) {
      console.log('[UCB] Platform not supported:', window.location.hostname);
      return;
    }

    // Check if extension is enabled
    const storage = await chrome.storage.local.get(['extensionEnabled', 'enabledPlatforms']);
    isEnabled = storage.extensionEnabled !== false;
    
    if (!isEnabled) {
      console.log('[UCB] Extension disabled');
      return;
    }

    // Load adapter config
    try {
      const response = await fetch(chrome.runtime.getURL(`adapters/${currentPlatform}.json`));
      adapterConfig = await response.json();
      console.log('[UCB] Loaded adapter:', currentPlatform);
    } catch (error) {
      console.error('[UCB] Failed to load adapter:', error);
      return;
    }

    // Check whitelist
    if (storage.enabledPlatforms && !storage.enabledPlatforms.includes(window.location.hostname)) {
      console.log('[UCB] Domain not whitelisted');
      return;
    }

    // Start observing
    startObserving();
    
    // Notify background script
    chrome.runtime.sendMessage({
      type: 'chat_opened',
      platform: currentPlatform
    });
  }

  // Start MutationObserver to detect chat windows
  function startObserving() {
    console.log('[UCB] Starting DOM observer');

    // Main observer for DOM changes
    observer = new MutationObserver((mutations) => {
      detectChatWindow();
      extractMessages();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style']
    });

    // Initial detection
    detectChatWindow();
    extractMessages();
  }

  // Detect if a chat window is currently open
  function detectChatWindow() {
    if (!adapterConfig) return;

    const chatContainer = document.querySelector(adapterConfig.selectors.chat_container);
    const isOpen = !!chatContainer;

    // Chat state changed
    if (isOpen && !window.ucbChatOpen) {
      window.ucbChatOpen = true;
      console.log('[UCB] Chat window opened');
      
      // Start observing the chat container specifically
      if (chatContainer && !chatObserver) {
        chatObserver = new MutationObserver(() => {
          extractMessages();
        });
        chatObserver.observe(chatContainer, {
          childList: true,
          subtree: true
        });
      }
      
      chrome.runtime.sendMessage({
        type: 'chat_opened',
        platform: currentPlatform
      });
      
    } else if (!isOpen && window.ucbChatOpen) {
      window.ucbChatOpen = false;
      console.log('[UCB] Chat window closed');
      
      if (chatObserver) {
        chatObserver.disconnect();
        chatObserver = null;
      }
      
      chrome.runtime.sendMessage({
        type: 'chat_closed',
        platform: currentPlatform
      });
    }
  }

  // Extract messages from the chat
  function extractMessages() {
    if (!adapterConfig || !window.ucbChatOpen) return;

    const messageElements = document.querySelectorAll(adapterConfig.selectors.messages);
    
    messageElements.forEach((msgEl) => {
      const messageId = msgEl.getAttribute('data-id') || msgEl.id || generateMessageId(msgEl);
      
      if (lastMessages.has(messageId)) return;
      
      const textEl = msgEl.querySelector(adapterConfig.selectors.message_text);
      const text = textEl ? textEl.innerText : msgEl.innerText;
      
      if (!text || text.trim() === '') return;
      
      // Determine if message is from self
      const isOwn = isOwnMessage(msgEl);
      
      // Extract sender
      const sender = extractSender(msgEl, isOwn);
      
      // Extract timestamp
      const timestamp = extractTimestamp(msgEl);
      
      const messageData = {
        id: messageId,
        text: text.trim(),
        sender: sender,
        isOwn: isOwn,
        timestamp: timestamp,
        platform: currentPlatform,
        url: window.location.href
      };
      
      lastMessages.add(messageId);
      
      // Keep set size manageable
      if (lastMessages.size > 1000) {
        const first = lastMessages.values().next().value;
        lastMessages.delete(first);
      }
      
      console.log('[UCB] New message:', messageData);
      
      // Send to background script
      chrome.runtime.sendMessage({
        type: 'message_detected',
        data: messageData
      });
    });
  }

  // Check if message is from the current user
  function isOwnMessage(msgEl) {
    // Platform-specific checks
    if (currentPlatform === 'whatsapp') {
      return msgEl.classList.contains('message-out') || 
             msgEl.getAttribute('data-testid')?.includes('outgoing') ||
             msgEl.closest('[data-testid="outgoing-message"]') !== null;
    }
    
    if (currentPlatform === 'telegram') {
      return msgEl.classList.contains('bubble-out') ||
             msgEl.classList.contains('is-out');
    }
    
    // Generic fallback - check for common patterns
    return msgEl.classList.contains('out') || 
           msgEl.classList.contains('outgoing') ||
           msgEl.classList.contains('me') ||
           msgEl.classList.contains('own');
  }

  // Extract sender name
  function extractSender(msgEl, isOwn) {
    if (isOwn) return 'self';
    
    // Try to find sender element
    const selectors = [
      '[data-testid="sender-name"]',
      '.sender-name',
      '.message-sender',
      '.from_name',
      '[data-peer-id]'
    ];
    
    for (const selector of selectors) {
      const senderEl = msgEl.querySelector(selector) || 
                       msgEl.closest('.message')?.querySelector(selector);
      if (senderEl) {
        return senderEl.innerText.trim() || senderEl.getAttribute('data-peer-id') || 'unknown';
      }
    }
    
    return 'unknown';
  }

  // Extract timestamp
  function extractTimestamp(msgEl) {
    const timeEl = msgEl.querySelector('time, [datetime], .time, .timestamp, .message-time');
    if (timeEl) {
      const datetime = timeEl.getAttribute('datetime') || timeEl.innerText;
      if (datetime) {
        return new Date(datetime).getTime() || Date.now();
      }
    }
    return Date.now();
  }

  // Generate unique ID for message element
  function generateMessageId(msgEl) {
    const text = msgEl.innerText.substring(0, 50);
    const timestamp = Date.now();
    return `${text}_${timestamp}`;
  }

  // Send a message to the chat
  async function sendMessage(text) {
    if (!adapterConfig || !window.ucbChatOpen) {
      console.error('[UCB] Cannot send message - chat not open');
      return false;
    }
    
    const inputEl = document.querySelector(adapterConfig.selectors.input);
    if (!inputEl) {
      console.error('[UCB] Input field not found');
      return false;
    }
    
    // Focus input
    inputEl.focus();
    
    // Set text
    inputEl.innerText = text;
    
    // Trigger input event
    inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    
    // Click send button if available
    if (adapterConfig.selectors.send_button) {
      const sendBtn = document.querySelector(adapterConfig.selectors.send_button);
      if (sendBtn) {
        sendBtn.click();
        return true;
      }
    }
    
    // Fallback: trigger Enter key
    inputEl.dispatchEvent(new KeyboardEvent('keydown', { 
      key: 'Enter', 
      code: 'Enter', 
      keyCode: 13,
      bubbles: true 
    }));
    
    return true;
  }

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'sendMessage') {
      const success = sendMessage(request.text);
      sendResponse({ success });
    }
    return true;
  });

  // Handle tab visibility change
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      extractMessages();
    }
  });

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
