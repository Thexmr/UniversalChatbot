/**
 * UniversalChatbot Configuration
 * Settings for SmartTask AI Integration
 */

const CONFIG = {
  // SmartTask AI Integration
  smarttask: {
    enabled: true,                    // Enable/disable SmartTask integration
    webhookUrl: 'http://localhost:8000/api/openclaw/webhook',
    agentId: 'universalchatbot',
    autoCreateTasks: true,            // Automatically create tasks on incoming messages
    includeOutgoing: false            // Include own/outgoing messages as tasks
  },
  
  // Storage keys
  storageKeys: {
    smarttaskEnabled: 'smarttaskEnabled',
    smarttaskUrl: 'smarttaskWebhookUrl'
  }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}