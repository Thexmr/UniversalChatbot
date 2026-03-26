// Native Messaging Host integration
// This file handles the connection between Chrome Extension and the native application

const NativeMessaging = {
  hostName: 'com.universalchatbot.bridge',
  port: null,
  isConnected: false,
  messageQueue: [],

  init() {
    this.connect();
  },

  connect() {
    if (this.port) {
      return;
    }

    try {
      this.port = chrome.runtime.connectNative(this.hostName);
      this.isConnected = true;

      this.port.onMessage.addListener((message) => {
        this.onMessage(message);
      });

      this.port.onDisconnect.addListener(() => {
        console.log('Native host disconnected');
        this.isConnected = false;
        this.port = null;
        
        // Retry connection
        setTimeout(() => this.connect(), 5000);
      });

      // Flush queued messages
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift();
        this.send(msg);
      }
    } catch (error) {
      console.error('Failed to connect to native host:', error);
    }
  },

  send(message) {
    if (this.port && this.isConnected) {
      this.port.postMessage(message);
    } else {
      this.messageQueue.push(message);
    }
  },

  onMessage(message) {
    // Handle messages from native host
    if (message.type === 'response') {
      console.log('Received response from native host:', message);
    }
  }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = NativeMessaging;
}
