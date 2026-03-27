// Background Service Worker - handles Native Messaging Host connection and updates

const NATIVE_HOST_NAME = 'com.universalchatbot.bridge';
let nativePort = null;
let isConnected = false;
let updateCheckInterval = null;

// Initialize connection to Native Messaging Host
function connectNativeHost() {
  if (nativePort) {
    console.log('[UCB] Already connected to native host');
    return;
  }

  try {
    nativePort = chrome.runtime.connectNative(NATIVE_HOST_NAME);
    isConnected = true;
    console.log('[UCB] Connected to native host');

    nativePort.onMessage.addListener((message) => {
      console.log('[UCB] Received from native:', message);
      handleNativeMessage(message);
    });

    nativePort.onDisconnect.addListener((p) => {
      const error = chrome.runtime.lastError;
      if (error) {
        console.error('[UCB] Native host disconnected with error:', error.message);
      } else {
        console.log('[UCB] Native host disconnected');
      }
      nativePort = null;
      isConnected = false;
      
      // Attempt to reconnect after delay
      setTimeout(connectNativeHost, 5000);
    });
  } catch (error) {
    console.error('[UCB] Failed to connect to native host:', error);
    nativePort = null;
    isConnected = false;
  }
}

// Handle messages from Native Messaging Host
function handleNativeMessage(message) {
  if (message.type === 'send_message') {
    // Forward to content script
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: 'sendMessage',
          text: message.text
        });
      }
    });
  } else if (message.type === 'enable_platform') {
    chrome.storage.local.set({ enabledPlatforms: message.platforms });
  }
}

// Send message to Native Messaging Host
function sendToNative(message) {
  if (!nativePort) {
    console.error('[UCB] Cannot send - native host not connected');
    return false;
  }
  
  try {
    nativePort.postMessage(message);
    return true;
  } catch (error) {
    console.error('[UCB] Failed to send to native host:', error);
    return false;
  }
}

// ============================================
// UPDATE CHECKING FUNCTIONALITY
// ============================================

const UPDATE_CHECK_INTERVAL = 60 * 60 * 1000; // 1 hour
const GITHUB_REPO = 'Thexmr/UniversalChatbot';

/**
 * Check for updates from GitHub releases
 */
async function checkForUpdates() {
  try {
    // Don't check if user dismissed recently (within 24h)
    const storage = await chrome.storage.local.get(['updateDismissed', 'updateCheckTime']);
    const now = Date.now();
    
    if (storage.updateDismissed && (now - storage.updateDismissed) < 24 * 60 * 60 * 1000) {
      console.log('[UCB] Update check skipped - recently dismissed');
      return;
    }
    
    // Rate limiting
    if (storage.updateCheckTime && (now - storage.updateCheckTime) < 5 * 60 * 1000) {
      console.log('[UCB] Update check skipped - rate limited');
      return;
    }
    
    await chrome.storage.local.set({ updateCheckTime: now });
    
    const response = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`, {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'UniversalChatbot-Extension'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const release = await response.json();
    const latestVersion = release.tag_name.replace(/^v/, '');
    const currentVersion = chrome.runtime.getManifest().version;
    
    console.log(`[UCB] Version check: ${currentVersion} vs ${latestVersion}`);
    
    if (isNewerVersion(latestVersion, currentVersion)) {
      const updateInfo = {
        version: latestVersion,
        current: currentVersion,
        url: release.html_url,
        notes: release.body,
        assets: release.assets,
        checkedAt: now
      };
      
      // Save update state
      await chrome.storage.local.set({
        hasUpdate: true,
        updateInfo: updateInfo
      });
      
      // Show badge on extension icon
      chrome.action.setBadgeText({ text: '1' });
      chrome.action.setBadgeBackgroundColor({ color: '#ff9800' });
      
      console.log('[UCB] Update available:', latestVersion);
      
      // Optional: Show notification
      showUpdateNotification(latestVersion, currentVersion);
    } else {
      // Clear update state if on latest
      await chrome.storage.local.set({ hasUpdate: false });
      chrome.action.setBadgeText({ text: '' });
    }
    
  } catch (error) {
    console.error('[UCB] Update check failed:', error);
  }
}

/**
 * Compare two version strings
 */
function isNewerVersion(latest, current) {
  const parseVersion = (v) => v.split('.').map(Number);
  const latestParts = parseVersion(latest);
  const currentParts = parseVersion(current);
  
  for (let i = 0; i < Math.max(latestParts.length, currentParts.length); i++) {
    const l = latestParts[i] || 0;
    const c = currentParts[i] || 0;
    if (l > c) return true;
    if (l < c) return false;
  }
  return false;
}

/**
 * Show browser notification for update
 */
function showUpdateNotification(newVersion, currentVersion) {
  chrome.notifications.create('update-available', {
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: 'Universal Chatbot Update Available',
    message: `Version ${newVersion} is ready to install (you have ${currentVersion})`,
    buttons: [
      { title: 'Update Now' },
      { title: 'Later' }
    ],
    priority: 1
  });
}

/**
 * Handle notification button clicks
 */
chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
  if (notificationId === 'update-available') {
    if (buttonIndex === 0) {
      // Update Now - open popup
      chrome.tabs.create({
        url: 'https://github.com/Thexmr/UniversalChatbot/releases/latest'
      });
    } else {
      // Later - dismiss for 24h
      chrome.storage.local.set({ updateDismissed: Date.now() });
    }
    chrome.notifications.clear(notificationId);
  }
});

/**
 * Clear update badge
 */
function clearUpdateBadge() {
  chrome.action.setBadgeText({ text: '' });
}

// ============================================
// MESSAGE HANDLING
// ============================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[UCB] Received from content script:', request);
  
  switch (request.type) {
    case 'message_detected':
      sendToNative({
        type: 'incoming_message',
        data: request.data,
        url: sender.url,
        timestamp: Date.now()
      });
      break;
      
    case 'chat_opened':
      sendToNative({
        type: 'chat_opened',
        url: sender.url,
        timestamp: Date.now()
      });
      break;
      
    case 'chat_closed':
      sendToNative({
        type: 'chat_closed',
        url: sender.url,
        timestamp: Date.now()
      });
      break;
      
    case 'get_status':
      sendResponse({ connected: isConnected });
      break;
      
    case 'reconnect_native':
      connectNativeHost();
      sendResponse({ success: true });
      break;
      
    case 'check_update':
      checkForUpdates().then(() => {
        chrome.storage.local.get(['hasUpdate', 'updateInfo'], (storage) => {
          sendResponse({ 
            hasUpdate: storage.hasUpdate || false, 
            info: storage.updateInfo 
          });
        });
      });
      return true; // Keep channel open
      
    case 'get_update_status':
      chrome.storage.local.get(['hasUpdate', 'updateInfo'], (storage) => {
        sendResponse({
          hasUpdate: storage.hasUpdate || false,
          info: storage.updateInfo || null
        });
      });
      return true;
      
    case 'dismiss_update':
      chrome.storage.local.set({ updateDismissed: Date.now() });
      clearUpdateBadge();
      sendResponse({ success: true });
      break;
      
    case 'start_update':
      // Trigger update process
      chrome.storage.local.get(['updateInfo'], async (storage) => {
        if (storage.updateInfo && storage.updateInfo.url) {
          // Open releases page for manual update
          chrome.tabs.create({ 
            url: storage.updateInfo.url 
          });
          sendResponse({ success: true });
        } else {
          sendResponse({ success: false, error: 'No update info' });
        }
      });
      return true; // Keep channel open
  }
  
  return true;
});

// ============================================
// INITIALIZATION
// ============================================

chrome.runtime.onStartup.addListener(() => {
  console.log('[UCB] Extension started');
  connectNativeHost();
  
  // Check for updates on startup
  checkForUpdates();
  
  // Start periodic update checks
  updateCheckInterval = setInterval(checkForUpdates, UPDATE_CHECK_INTERVAL);
});

chrome.runtime.onInstalled.addListener((details) => {
  console.log('[UCB] Extension installed/updated');
  connectNativeHost();
  
  // Set default enabled platforms
  chrome.storage.local.set({
    enabledPlatforms: ['web.whatsapp.com', 'web.telegram.org'],
    extensionEnabled: true
  });
  
  // Check for updates
  checkForUpdates();
  
  // Start periodic update checks
  if (updateCheckInterval) clearInterval(updateCheckInterval);
  updateCheckInterval = setInterval(checkForUpdates, UPDATE_CHECK_INTERVAL);
  
  // Show welcome notification on first install
  if (details.reason === 'install') {
    chrome.notifications.create('welcome', {
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'Universal Chatbot Installed',
      message: 'Your AI chatbot assistant is ready! Open the dashboard at http://localhost:5000',
      priority: 1
    });
  }
});

// Initial connection
connectNativeHost();

console.log('[UCB] Background service worker loaded');