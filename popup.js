/**
 * Universal Chatbot Popup
 * Handles UI interactions, real-time status updates, and platform toggles
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize Lucide icons
  lucide.createIcons();

  // Cache DOM elements
  const elements = {
    statusDot: document.getElementById('status-dot'),
    statusText: document.getElementById('status-text'),
    statusSubtext: document.getElementById('status-subtext'),
    extensionToggle: document.getElementById('extension-toggle'),
    whatsappToggle: document.getElementById('whatsapp-toggle'),
    telegramToggle: document.getElementById('telegram-toggle'),
    discordToggle: document.getElementById('discord-toggle'),
    reconnectBtn: document.getElementById('reconnect-btn'),
    dashboardBtn: document.getElementById('open-dashboard'),
    settingsLink: document.getElementById('settings-link'),
    helpLink: document.getElementById('help-link'),
    platformToggles: document.querySelectorAll('.platform-toggles .toggle-switch input'),
    toggleItems: document.querySelectorAll('.toggle-item')
  };

  // State
  const state = {
    isExtensionEnabled: true,
    enabledPlatforms: ['whatsapp', 'telegram', 'discord'],
    connectionStatus: 'connecting', // 'connected', 'connecting', 'disconnected'
    isReconnecting: false
  };

  // Initialize
  await loadSettings();
  updatePlatformTogglesState();
  await checkStatus();
  setupEventListeners();
  startStatusPolling();

  /**
   * Load saved settings from storage
   */
  async function loadSettings() {
    try {
      const storage = await chrome.storage.local.get([
        'extensionEnabled',
        'enabledPlatforms',
        'platformStates'
      ]);

      // Extension enabled state
      state.isExtensionEnabled = storage.extensionEnabled !== false;
      elements.extensionToggle.checked = state.isExtensionEnabled;

      // Platform states
      const platformStates = storage.platformStates || {
        whatsapp: true,
        telegram: true,
        discord: true
      };

      elements.whatsappToggle.checked = platformStates.whatsapp ?? true;
      elements.telegramToggle.checked = platformStates.telegram ?? true;
      elements.discordToggle.checked = platformStates.discord ?? true;

      // Update state array
      updateEnabledPlatforms();
    } catch (error) {
      console.error('Error loading settings:', error);
      // Use defaults
    }
  }

  /**
   * Update the enabled platforms array based on toggle states
   */
  function updateEnabledPlatforms() {
    state.enabledPlatforms = [];
    if (elements.whatsappToggle.checked) state.enabledPlatforms.push('whatsapp');
    if (elements.telegramToggle.checked) state.enabledPlatforms.push('telegram');
    if (elements.discordToggle.checked) state.enabledPlatforms.push('discord');
  }

  /**
   * Update visual state of platform toggles based on extension enabled state
   */
  function updatePlatformTogglesState() {
    const platformItems = document.querySelectorAll('.platforms-section .toggle-item');
    
    platformItems.forEach(item => {
      if (state.isExtensionEnabled) {
        item.classList.remove('disabled');
        item.querySelector('input').disabled = false;
      } else {
        item.classList.add('disabled');
        item.querySelector('input').disabled = true;
      }
    });
  }

  /**
   * Set up event listeners
   */
  function setupEventListeners() {
    // Extension toggle
    elements.extensionToggle.addEventListener('change', async () => {
      state.isExtensionEnabled = elements.extensionToggle.checked;
      await chrome.storage.local.set({ extensionEnabled: state.isExtensionEnabled });
      updatePlatformTogglesState();
      
      // Update status subtext
      if (state.isExtensionEnabled) {
        updateStatusIndicator(state.connectionStatus);
      } else {
        updateStatusUI('disconnected', 'Extension Disabled', 'toggle to enable');
      }
    });

    // Platform toggles
    const platformMap = {
      'whatsapp-toggle': 'whatsapp',
      'telegram-toggle': 'telegram',
      'discord-toggle': 'discord'
    };

    Object.entries(platformMap).forEach(([toggleId, platform]) => {
      const toggle = document.getElementById(toggleId);
      toggle.addEventListener('change', async () => {
        updateEnabledPlatforms();
        
        const platformStates = {
          whatsapp: elements.whatsappToggle.checked,
          telegram: elements.telegramToggle.checked,
          discord: elements.discordToggle.checked
        };
        
        await chrome.storage.local.set({ platformStates });
        
        // Notify background script
        notifyBackground('platforms_changed', { platforms: state.enabledPlatforms });
      });
    });

    // Reconnect button
    elements.reconnectBtn.addEventListener('click', async () => {
      if (state.isReconnecting) return;
      
      state.isReconnecting = true;
      elements.reconnectBtn.disabled = true;
      elements.reconnectBtn.querySelector('span').textContent = 'Reconnecting...';
      
      updateStatusUI('connecting', 'Reconnecting...', 'please wait');
      
      try {
        const response = await notifyBackground('reconnect_native');
        
        // Wait a moment for reconnection attempt
        await new Promise(resolve => setTimeout(resolve, 1500));
        await checkStatus();
      } catch (error) {
        console.error('Reconnect failed:', error);
        updateStatusUI('disconnected', 'Connection Failed', 'try again');
      } finally {
        state.isReconnecting = false;
        elements.reconnectBtn.disabled = false;
        elements.reconnectBtn.querySelector('span').textContent = 'Reconnect';
      }
    });

    // Dashboard button
    elements.dashboardBtn.addEventListener('click', () => {
      // Open dashboard in new tab
      const dashboardUrl = chrome.runtime.getURL('dashboard.html');
      chrome.tabs.create({ url: dashboardUrl });
    });

    // Settings link
    elements.settingsLink.addEventListener('click', (e) => {
      e.preventDefault();
      const settingsUrl = chrome.runtime.getURL('settings.html');
      chrome.tabs.create({ url: settingsUrl });
    });

    // Help link
    elements.helpLink.addEventListener('click', (e) => {
      e.preventDefault();
      const helpUrl = 'https://github.com/Thexmr/UniversalChatbot#readme';
      chrome.tabs.create({ url: helpUrl });
    });
  }

  /**
   * Check native host connection status
   */
  async function checkStatus() {
    if (!state.isExtensionEnabled) {
      updateStatusUI('disconnected', 'Extension Disabled', 'toggle to enable');
      return;
    }

    try {
      const response = await notifyBackground('get_status');
      
      if (response && response.connected) {
        state.connectionStatus = 'connected';
        updateStatusUI('connected', 'Connected', 'native host ready');
      } else {
        state.connectionStatus = 'disconnected';
        updateStatusUI('disconnected', 'Disconnected', 'click reconnect');
      }
    } catch (error) {
      console.error('Status check failed:', error);
      state.connectionStatus = 'disconnected';
      updateStatusUI('disconnected', 'Extension Error', 'check installation');
    }
  }

  /**
   * Update status indicator UI
   */
  function updateStatusIndicator(status) {
    elements.statusDot.className = 'status-indicator';
    elements.statusDot.classList.add(status);
  }

  /**
   * Update complete status UI
   */
  function updateStatusUI(status, text, subtext) {
    updateStatusIndicator(status);
    elements.statusText.textContent = text;
    elements.statusSubtext.textContent = subtext;
  }

  /**
   * Start periodic status polling (every 5 seconds)
   */
  function startStatusPolling() {
    // Check immediately and then every 5 seconds
    setInterval(async () => {
      if (state.isExtensionEnabled && !state.isReconnecting) {
        await checkStatus();
      }
    }, 5000);
  }

  /**
   * Send message to background script
   */
  async function notifyBackground(type, data = {}) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type, ...data }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
  }

  // Expose update function for external calls
  window.updatePopupStatus = checkStatus;
});
