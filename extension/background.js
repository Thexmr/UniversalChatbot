// Background Service Worker - handles Native Messaging Host connection

const NATIVE_HOST_NAME = 'com.universalchatbot.bridge';
let nativePort = null;
let isConnected = false;

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

// Handle messages from content scripts
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
  }
  
  return true;
});

// Initialize on startup
chrome.runtime.onStartup.addListener(() => {
  console.log('[UCB] Extension started');
  connectNativeHost();
});

chrome.runtime.onInstalled.addListener(() => {
  console.log('[UCB] Extension installed');
  connectNativeHost();
  
  // Set default enabled platforms
  chrome.storage.local.set({
    enabledPlatforms: ['web.whatsapp.com', 'web.telegram.org'],
    extensionEnabled: true
  });
});

// Initial connection
connectNativeHost();
