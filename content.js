// Content Script - runs on supported chat platforms
// Detects chat windows, extracts messages, handles message sending
// Supports generic adapter system for multiple platforms

(function() {
  'use strict';

  let currentPlatform = null;
  let adapterConfig = null;
  let observer = null;
  let chatObserver = null;
  let isEnabled = false;
  let lastMessages = new Set();

  // Platform detection with improved domain matching
  function detectPlatform() {
    const host = window.location.hostname;
    if (host.includes('whatsapp')) return 'web.whatsapp.com';
    if (host.includes('telegram')) return 'web.telegram.org';
    if (host.includes('discord')) return 'discord.com';
    return 'generic';
  }

  // Load platform config from adapters registry
  async function loadAdapter(domain) {
    try {
      const adapters = await fetch(chrome.runtime.getURL('adapters/adapters.json'))
        .then(r => r.json());
      
      const adapterFile = adapters[domain] || adapters['generic'];
      const config = await fetch(chrome.runtime.getURL(`adapters/${adapterFile}`))
        .then(r => r.json());
      
      return config;
    } catch (error) {
      console.error('[UCB] Failed to load adapter for domain:', domain, error);
      return null;
    }
  }

  // Initialize the content script
  async function init() {
    currentPlatform = detectPlatform();
    
    if (currentPlatform === 'generic') {
      console.log('[UCB] Platform not specifically supported:', window.location.hostname);
      // Optionally still try generic adapter
      // return;
    }

    // Check if extension is enabled
    const storage = await chrome.storage.local.get(['extensionEnabled', 'enabledPlatforms']);
    isEnabled = storage.extensionEnabled !== false;
    
    if (!isEnabled) {
      console.log('[UCB] Extension disabled');
      return;
    }

    // Load adapter config using new generic system
    adapterConfig = await loadAdapter(currentPlatform);
    if (!adapterConfig) {
      console.error('[UCB] Failed to load adapter config');
      return;
    }
    
    console.log('[UCB] Loaded adapter:', adapterConfig.name);

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
        const observerTarget = adapterConfig.selectors.list_mutation 
          ? document.querySelector(adapterConfig.selectors.list_mutation) || chatContainer
          : chatContainer;
          
        chatObserver = new MutationObserver((mutations) => {
          extractMessages();
        });
        chatObserver.observe(observerTarget, {
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

  // Check if message is from the current user
  function isOwnMessage(msgEl) {
    if (!adapterConfig) return false;

    const platform = detectPlatform();

    // Platform-specific checks
    if (platform === 'web.whatsapp.com') {
      return msgEl.classList.contains('message-out') || 
             msgEl.getAttribute('data-testid')?.includes('outgoing') ||
             msgEl.closest('[data-testid="outgoing-message"]') !== null;
    }
    
    if (platform === 'web.telegram.org') {
      return msgEl.classList.contains('bubble-out') ||
             msgEl.classList.contains('is-out');
    }
    
    if (platform === 'discord.com') {
      // Discord uses React and dynamic classes
      // Check for own message indicators
      const ownIndicator = adapterConfig.selectors.own_message_indicator;
      if (ownIndicator && msgEl.querySelector(ownIndicator)) {
        return true;
      }
      // Check class patterns typical for own messages
      return msgEl.classList.value.includes('groupStart') === false ||
             msgEl.getAttribute('data-is-author-self') === 'true';
    }
    
    // Generic fallback - check for common patterns
    return msgEl.classList.contains('out') || 
           msgEl.classList.contains('outgoing') ||
           msgEl.classList.contains('me') ||
           msgEl.classList.contains('own') ||
           msgEl.closest('.outgoing, .me, .own') !== null;
  }

  // Extract sender name
  function extractSender(msgEl, isOwn) {
    if (isOwn) return 'self';
    
    if (adapterConfig && adapterConfig.selectors.message_author) {
      const authorEl = msgEl.querySelector(adapterConfig.selectors.message_author);
      if (authorEl) {
        return authorEl.innerText.trim() || authorEl.getAttribute('aria-label') || 'unknown';
      }
    }
    
    // Generic fallback selectors
    const selectors = [
      '[data-testid="sender-name"]',
      '.sender-name',
      '.message-sender',
      '.from_name',
      '.author',
      '[data-author]',
      '[data-peer-id]'
    ];
    
    for (const selector of selectors) {
      const senderEl = msgEl.querySelector(selector) || 
                       msgEl.closest('.message')?.querySelector(selector);
      if (senderEl) {
        return senderEl.innerText.trim() || 
               senderEl.getAttribute('data-peer-id') || 
               senderEl.getAttribute('data-author') || 
               'unknown';
      }
    }
    
    return 'unknown';
  }

  // Extract timestamp
  function extractTimestamp(msgEl) {
    if (adapterConfig && adapterConfig.selectors.message_timestamp) {
      const timeEl = msgEl.querySelector(adapterConfig.selectors.message_timestamp);
      if (timeEl) {
        const datetime = timeEl.getAttribute('datetime') || timeEl.innerText;
        if (datetime) {
          const parsed = new Date(datetime).getTime();
          return isNaN(parsed) ? Date.now() : parsed;
        }
      }
    }
    
    // Generic fallback
    const timeEl = msgEl.querySelector('time, [datetime], .time, .timestamp, .message-time');
    if (timeEl) {
      const datetime = timeEl.getAttribute('datetime') || timeEl.innerText;
      if (datetime) {
        const parsed = new Date(datetime).getTime();
        return isNaN(parsed) ? Date.now() : parsed;
      }
    }
    return Date.now();
  }

  // Generate unique ID for message element
  function generateMessageId(msgEl) {
    // Try to find existing ID
    const existingId = msgEl.getAttribute('data-id') || 
                       msgEl.getAttribute('id') ||
                       msgEl.getAttribute('data-message-id');
    if (existingId) return existingId;
    
    // Generate from content and timestamp
    const text = msgEl.innerText.substring(0, 50);
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `${text.substring(0, 20)}_${timestamp}_${random}`;
  }

  // Extract messages from the chat
  function extractMessages() {
    if (!adapterConfig || !window.ucbChatOpen) return;

    const messageElements = document.querySelectorAll(adapterConfig.selectors.messages);
    
    messageElements.forEach((msgEl) => {
      const messageId = generateMessageId(msgEl);
      
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
    
    // Handle different input types
    if (inputEl.isContentEditable) {
      // ContentEditable element (Discord, etc.)
      inputEl.innerText = text;
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      // Regular input/textarea
      inputEl.value = text;
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    // Trigger input events for React and other frameworks
    ['input', 'keydown', 'keyup', 'blur', 'focus'].forEach(eventType => {
      inputEl.dispatchEvent(new Event(eventType, { bubbles: true }));
    });
    
    // Click send button if available
    if (adapterConfig.selectors.send_button) {
      const sendBtn = document.querySelector(adapterConfig.selectors.send_button);
      if (sendBtn) {
        sendBtn.click();
        return true;
      }
    }
    
    // Fallback: trigger Enter key
    const enterEvent = new KeyboardEvent('keydown', { 
      key: 'Enter', 
      code: 'Enter', 
      keyCode: 13,
      which: 13,
      bubbles: true,
      cancelable: true
    });
    inputEl.dispatchEvent(enterEvent);
    
    // If not prevented, also try keypress
    if (!enterEvent.defaultPrevented) {
      inputEl.dispatchEvent(new KeyboardEvent('keypress', { 
        key: 'Enter', 
        code: 'Enter', 
        keyCode: 13,
        charCode: 13,
        which: 13,
        bubbles: true 
      }));
    }
    
    return true;
  }

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'sendMessage') {
      sendMessage(request.text).then(success => {
        sendResponse({ success });
      });
      return true; // Async response
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
