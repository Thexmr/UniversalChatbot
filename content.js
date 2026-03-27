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
    if (host.includes('slack')) return 'app.slack.com';
    if (host.includes('teams.microsoft')) return 'teams.microsoft.com';
    return 'generic';
  }

  // ==================== MS TEAMS SPECIFIC HANDLERS ====================

  // Detect MS Teams chat type (Channel, Private Chat, Meeting Chat)
  function detectTeamsChatType() {
    const url = window.location.href;
    const chatContainer = document.querySelector("[data-tid='chat-list']");
    
    if (!chatContainer) return 'unknown';
    
    // Check URL patterns for different chat types
    if (url.includes('/channel/')) {
      const channelName = document.querySelector("[data-tid='team-channel-name']")?.textContent?.trim();
      return { type: 'channel', name: channelName || 'unknown' };
    }
    
    if (url.includes('/chat/')) {
      const chatName = document.querySelector("[data-tid='chat-title']")?.textContent?.trim();
      return { type: 'private_chat', name: chatName || 'unknown' };
    }
    
    if (url.includes('/l/meetup-join/') || url.includes('/meeting/')) {
      const meetingTitle = document.querySelector("[data-tid='meeting-title']")?.textContent?.trim();
      return { type: 'meeting_chat', name: meetingTitle || 'unknown' };
    }
    
    // Fallback detection via DOM elements
    const teamHeader = document.querySelector("[data-tid='team-header']");
    if (teamHeader) {
      return { type: 'channel', name: teamHeader.textContent?.trim() || 'unknown' };
    }
    
    return { type: 'unknown', name: 'unknown' };
  }

  // Extract Teams message content with rich text support
  function extractTeamsMessageContent(msgEl) {
    const contentEl = msgEl.querySelector(".ui-chat__messagecontent");
    if (!contentEl) return { text: '', html: '', has_mentions: false };
    
    // Get plain text
    const text = contentEl.innerText || '';
    
    // Get HTML content for rich text analysis
    const html = contentEl.innerHTML || '';
    
    // Check for mentions (@user)
    const hasMentions = !!contentEl.querySelector("[data-tid='mention']");
    const mentions = [...contentEl.querySelectorAll("[data-tid='mention']")].map(el => el.textContent);
    
    // Check for formatted text
    const hasBold = !!contentEl.querySelector("strong, b");
    const hasItalic = !!contentEl.querySelector("em, i");
    const hasLinks = !!contentEl.querySelector("a");
    
    // Check for attachments/files
    const hasAttachments = !!msgEl.querySelector("[data-tid='attachment-card']");
    const attachments = [...msgEl.querySelectorAll("[data-tid='attachment-card'")].map(el => ({
      name: el.getAttribute('data-filename') || 'unknown',
      type: el.getAttribute('data-filetype') || 'unknown'
    }));
    
    // Check if message is a reply
    const isReply = !!msgEl.closest("[data-tid='thread-message']");
    const threadId = msgEl.closest("[data-tid='thread-container']")?.getAttribute('data-thread-id');
    
    return {
      text: text.trim(),
      html: html,
      has_mentions: hasMentions,
      mentions: mentions,
      has_bold: hasBold,
      has_italic: hasItalic,
      has_links: hasLinks,
      has_attachments: hasAttachments,
      attachments: attachments,
      is_reply: isReply,
      thread_id: threadId
    };
  }

  // Send message to MS Teams (CKEditor specific handling)
  async function sendTeamsMessage(text, options = {}) {
    const inputEl = document.querySelector("[data-tid='ckeditor']");
    if (!inputEl) {
      console.error('[UCB] Teams CKEditor input not found');
      return false;
    }
    
    // Find the contenteditable element inside CKEditor
    const editorEl = inputEl.querySelector("[contenteditable='true']") || inputEl;
    
    if (!editorEl.isContentEditable) {
      console.error('[UCB] Teams editor element is not contenteditable');
      return false;
    }
    
    // Focus the editor
    editorEl.focus();
    
    // Clear existing content
    editorEl.innerHTML = '';
    
    // Insert the message as HTML (Teams supports rich text)
    if (options.html) {
      editorEl.innerHTML = options.html;
    } else if (options.preserve_formatting) {
      // Convert newlines to <br> for Teams
      editorEl.innerHTML = text.replace(/\n/g, '<br>');
    } else {
      editorEl.innerText = text;
    }
    
    // Trigger React input events
    const inputEvent = new Event('input', { bubbles: true, cancelable: true });
    editorEl.dispatchEvent(inputEvent);
    
    // Trigger keydown for React state update
    editorEl.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
    editorEl.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
    
    // Wait for Teams to process
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Click send button if available
    const sendBtn = document.querySelector("[data-tid='send-message-button']");
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      return true;
    }
    
    // Fallback: Ctrl+Enter to send
    editorEl.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      ctrlKey: true,
      bubbles: true
    }));
    
    return true;
  }

  // Check if Teams presence/typing indicator is active
  function checkTeamsTypingIndicator() {
    const typingEl = document.querySelector('.ui-chat__typing-indicator');
    if (typingEl) {
      const typingUsers = [...typingEl.querySelectorAll("[data-tid='typing-user-name'")].map(el => el.textContent);
      return { is_typing: true, users: typingUsers };
    }
    return { is_typing: false, users: [] };
  }

  // ==================== END MS TEAMS HANDLERS ====================

  // Shadow DOM query helper - needed for platforms like Slack
  function queryShadowDOM(selector, shadowHost) {
    const host = typeof shadowHost === 'string' 
      ? document.querySelector(shadowHost) 
      : shadowHost;
    if (!host || !host.shadowRoot) return null;
    return host.shadowRoot.querySelector(selector);
  }

  // Deep query that traverses shadow DOM
  function queryDeep(selector, maxDepth = 5) {
    // Try regular query first
    const regular = document.querySelector(selector);
    if (regular) return regular;
    
    // Search through shadow roots
    function searchShadowRoots(root, depth) {
      if (depth > maxDepth) return null;
      
      // Find all elements with shadow roots
      const allElements = root.querySelectorAll('*');
      for (const el of allElements) {
        if (el.shadowRoot) {
          // Try query in this shadow root
          const found = el.shadowRoot.querySelector(selector);
          if (found) return found;
          
          // Recurse deeper
          const deeper = searchShadowRoots(el.shadowRoot, depth + 1);
          if (deeper) return deeper;
        }
      }
      return null;
    }
    
    return searchShadowRoots(document, 0);
  }

  // Query all elements through shadow DOM
  function queryAllDeep(selector, maxDepth = 5) {
    const results = [...document.querySelectorAll(selector)];
    
    function searchShadowRoots(root, depth) {
      if (depth > maxDepth) return;
      
      const allElements = root.querySelectorAll('*');
      for (const el of allElements) {
        if (el.shadowRoot) {
          results.push(...el.shadowRoot.querySelectorAll(selector));
          searchShadowRoots(el.shadowRoot, depth + 1);
        }
      }
    }
    
    searchShadowRoots(document, 0);
    return results;
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

  // Extract Slack thread info from message element
  function extractSlackThreadInfo(msgEl) {
    const threadIndicator = msgEl.querySelector('[data-qa="thread_indicator"]');
    if (threadIndicator) {
      return {
        is_thread: true,
        thread_id: msgEl.getAttribute('data-thread-id') || null,
        reply_count: threadIndicator.textContent.match(/\d+/)?.[0] || '0'
      };
    }
    return { is_thread: false };
  }

  // Detect Slack channel/DM type
  function detectSlackChatType() {
    const channelHeader = document.querySelector('.p-workspace__primary_view_contents');
    if (!channelHeader) return 'unknown';
    
    // Check for DM indicators
    const isDM = !!document.querySelector('.p-workspace__sidebar [data-qa="direct_messages"]');
    const isChannel = !!document.querySelector('.p-workspace__sidebar [data-qa="channels"]');
    
    // Get current channel/DM name
    const headerName = document.querySelector('.p-classic_nav__team_header__name,.p-view_header__title');
    const chatName = headerName?.textContent?.trim() || 'unknown';
    
    return {
      type: isDM ? 'dm' : (isChannel ? 'channel' : 'unknown'),
      name: chatName
    };
  }

  // Detect if a chat window is currently open
  function detectChatWindow() {
    if (!adapterConfig) return;

    // Use deep query for Shadow DOM support
    const chatContainer = adapterConfig.features?.uses_shadow_dom 
      ? queryDeep(adapterConfig.selectors.chat_container) 
      : document.querySelector(adapterConfig.selectors.chat_container);
    const isOpen = !!chatContainer;

    // Chat state changed
    if (isOpen && !window.ucbChatOpen) {
      window.ucbChatOpen = true;
      console.log('[UCB] Chat window opened');
      
      // Start observing the chat container specifically
      if (chatContainer && !chatObserver) {
        let observerTarget;
        
        if (adapterConfig.selectors.list_mutation) {
          // Use deep query for Shadow DOM support
          observerTarget = adapterConfig.features?.uses_shadow_dom
            ? queryDeep(adapterConfig.selectors.list_mutation)
            : document.querySelector(adapterConfig.selectors.list_mutation);
        }
        
        if (!observerTarget) {
          observerTarget = chatContainer;
        }
        
        // For Slack virtual scroll, also observe for lazy-loaded content
        const observerConfig = adapterConfig.features?.virtual_scroll 
          ? { childList: true, subtree: true, attributes: true }
          : { childList: true, subtree: true };
          
        chatObserver = new MutationObserver((mutations) => {
          // Handle virtual scroll - new items may appear
          if (adapterConfig.features?.virtual_scroll) {
            extractMessages();
            // Re-scan for new elements that might have appeared
            setTimeout(extractMessages, 100);
          } else {
            extractMessages();
          }
        });
        
        chatObserver.observe(observerTarget, observerConfig);
        
        // For Slack: also set up scroll listener to trigger extraction on virtual scroll
        if (adapterConfig.features?.virtual_scroll) {
          const scrollContainer = chatContainer.querySelector('[data-qa="virtual-list"]') || chatContainer;
          scrollContainer?.addEventListener('scroll', debounce(() => {
            extractMessages();
          }, 250));
        }
      }
      
      // Send platform-specific chat info
      let chatInfo = null;
      if (currentPlatform === 'app.slack.com') {
        chatInfo = detectSlackChatType();
      } else if (currentPlatform === 'teams.microsoft.com') {
        chatInfo = detectTeamsChatType();
      }
      
      chrome.runtime.sendMessage({
        type: 'chat_opened',
        platform: currentPlatform,
        chatInfo: chatInfo
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
    
    if (platform === 'app.slack.com') {
      // Slack own message detection
      // Slack uses c-message--sent class for own messages
      if (msgEl.classList.contains('c-message--sent') || 
          msgEl.closest('.c-message--sent')) {
        return true;
      }
      // Check via data-qa attributes
      if (msgEl.getAttribute('data-qa')?.includes('message-sent')) {
        return true;
      }
      // Check for sender match with current user
      const senderEl = msgEl.querySelector('.c-message__sender');
      if (senderEl) {
        // In Slack, we need to compare with current user's display name
        // This is a heuristic - self messages often have specific attributes
        const isFromSelf = msgEl.getAttribute('data-from-me') === 'true' ||
                          msgEl.querySelector('[data-qa="message-sent"]') !== null;
        return isFromSelf;
      }
      return false;
    }
    
    if (platform === 'teams.microsoft.com') {
      // Teams own message detection
      // Teams uses data-tid='message-from-me' for own messages
      if (msgEl.querySelector("[data-tid='message-from-me']")) {
        return true;
      }
      if (msgEl.getAttribute('data-tid')?.includes('from-me')) {
        return true;
      }
      // Check for own message class patterns
      if (msgEl.classList.contains('ui-chat__message--self') ||
          msgEl.classList.contains('ui-chat__message--own')) {
        return true;
      }
      // Check parent container for self indicator
      const parentEl = msgEl.closest("[data-tid='message-container']");
      if (parentEl?.getAttribute('data-is-self') === 'true') {
        return true;
      }
      return false;
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

  // Debounce helper for scroll events
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Extract messages from the chat
  function extractMessages() {
    if (!adapterConfig || !window.ucbChatOpen) return;

    // Use deep query for platforms with Shadow DOM
    const messageElements = adapterConfig.features?.uses_shadow_dom
      ? queryAllDeep(adapterConfig.selectors.messages)
      : document.querySelectorAll(adapterConfig.selectors.messages);
    
    // Handle Slack's virtual list - remove stale references
    const validElements = Array.from(messageElements).filter(el => document.contains(el) || el.isConnected);
    
    validElements.forEach((msgEl) => {
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
      
      // Add Slack-specific metadata
      if (currentPlatform === 'app.slack.com') {
        const threadInfo = extractSlackThreadInfo(msgEl);
        if (threadInfo.is_thread) {
          messageData.thread = threadInfo;
        }
      }
      
      // Add Teams-specific metadata with rich content extraction
      if (currentPlatform === 'teams.microsoft.com') {
        const teamsContent = extractTeamsMessageContent(msgEl);
        if (teamsContent) {
          messageData.html = teamsContent.html;
          messageData.has_rich_text = teamsContent.has_bold || teamsContent.has_italic || teamsContent.has_links;
          if (teamsContent.has_mentions) {
            messageData.mentions = teamsContent.mentions;
          }
          if (teamsContent.has_attachments) {
            messageData.attachments = teamsContent.attachments;
          }
          if (teamsContent.is_reply) {
            messageData.is_reply = true;
            messageData.thread_id = teamsContent.thread_id;
          }
        }
      }
      
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
  async function sendMessage(text, options = {}) {
    if (!adapterConfig || !window.ucbChatOpen) {
      console.error('[UCB] Cannot send message - chat not open');
      return false;
    }
    
    // MS Teams specific CKEditor handling
    if (currentPlatform === 'teams.microsoft.com') {
      return await sendTeamsMessage(text, options);
    }

    // Use deep query for Shadow DOM support
    const inputEl = adapterConfig.features?.uses_shadow_dom
      ? queryDeep(adapterConfig.selectors.input)
      : document.querySelector(adapterConfig.selectors.input);
      
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
      const sendBtn = adapterConfig.features?.uses_shadow_dom
        ? queryDeep(adapterConfig.selectors.send_button)
        : document.querySelector(adapterConfig.selectors.send_button);
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
