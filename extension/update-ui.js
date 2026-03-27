/**
 * UniversalChatbot Extension Update Notification Module
 * Handles update badges, notifications, and one-click updates
 */

(function() {
  'use strict';

  // Update state
  const UpdateState = {
    hasUpdate: false,
    updateInfo: null,
    checked: false
  };

  const UPDATE_CHECK_INTERVAL = 60 * 60 * 1000; // 1 hour

  // Badge colors for different states
  const BadgeColors = {
    default: '#667eea',    // Normal
    update: '#ff9800',     // Update available
    error: '#f44336'       // Error
  };

  /**
   * Check for updates from GitHub
   */
  async function checkForUpdates() {
    try {
      const GITHUB_API_URL = 'https://api.github.com/repos/Thexmr/UniversalChatbot/releases/latest';
      
      const response = await fetch(GITHUB_API_URL, {
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
      
      // Get current version from manifest
      const currentVersion = chrome.runtime.getManifest().version;
      
      // Simple version comparison
      const hasUpdate = isNewerVersion(latestVersion, currentVersion);
      
      if (hasUpdate) {
        UpdateState.hasUpdate = true;
        UpdateState.updateInfo = {
          version: latestVersion,
          current: currentVersion,
          url: release.html_url,
          notes: release.body,
          assets: release.assets
        };
        
        // Save state
        await chrome.storage.local.set({
          'hasUpdate': true,
          'updateInfo': UpdateState.updateInfo,
          'lastUpdateCheck': Date.now()
        });
        
        // Show badge
        showUpdateBadge();
        
        console.log('[UCB] Update available:', latestVersion);
      } else {
        UpdateState.hasUpdate = false;
        await chrome.storage.local.set({
          'hasUpdate': false,
          'lastUpdateCheck': Date.now()
        });
        clearBadge();
      }
      
      UpdateState.checked = true;
      return hasUpdate;
      
    } catch (error) {
      console.error('[UCB] Update check failed:', error);
      return false;
    }
  }

  /**
   * Compare versions
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
   * Show update badge on extension icon
   */
  function showUpdateBadge() {
    if (!UpdateState.hasUpdate) return;
    
    chrome.action.setBadgeText({ text: '1' });
    chrome.action.setBadgeBackgroundColor({ color: BadgeColors.update });
    chrome.action.setBadgeTextColor({ color: '#fff' });
  }

  /**
   * Clear badge
   */
  function clearBadge() {
    chrome.action.setBadgeText({ text: '' });
  }

  /**
   * Get update info from storage
   */
  async function getUpdateInfo() {
    const storage = await chrome.storage.local.get(['hasUpdate', 'updateInfo']);
    return {
      hasUpdate: storage.hasUpdate || false,
      updateInfo: storage.updateInfo || null
    };
  }

  /**
   * Create update notification HTML
   */
  function createUpdateNotification(updateInfo) {
    const div = document.createElement('div');
    div.className = 'ucb-update-notification';
    div.innerHTML = `
      <div class="ucb-update-header">
        <span class="ucb-update-icon">🔄</span>
        <span class="ucb-update-title">Update Available!</span>
      </div>
      <div class="ucb-update-body">
        <p>Version <strong>${escapeHtml(updateInfo.version)}</strong> is now available</p>
        <p class="ucb-update-current">Current: ${escapeHtml(updateInfo.current)}</p>
      </div>
      <div class="ucb-update-actions">
        <button class="ucb-btn ucb-btn-primary" id="ucb-update-now">Update Now</button>
        <button class="ucb-btn ucb-btn-secondary" id="ucb-update-later">Later</button>
        <button class="ucb-btn ucb-btn-link" id="ucb-update-release">What's New</button>
      </div>
    `;
    return div;
  }

  /**
   * Escape HTML
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show update popup/modal
   */
  function showUpdatePopup() {
    if (!UpdateState.updateInfo) return;
    
    // Remove existing notification
    const existing = document.getElementById('ucb-update-popup');
    if (existing) existing.remove();
    
    // Create popup container
    const popup = document.createElement('div');
    popup.id = 'ucb-update-popup';
    popup.innerHTML = `
      <style>
        #ucb-update-popup {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 2147483647;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .ucb-update-notification {
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
          border: 1px solid #667eea;
          border-radius: 12px;
          padding: 16px 20px;
          min-width: 320px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(102,126,234,0.3);
          animation: ucb-slideIn 0.3s ease-out;
        }
        @keyframes ucb-slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        .ucb-update-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 12px;
        }
        .ucb-update-icon {
          font-size: 20px;
        }
        .ucb-update-title {
          font-size: 16px;
          font-weight: 600;
          color: #fff;
        }
        .ucb-update-body {
          margin-bottom: 16px;
        }
        .ucb-update-body p {
          margin: 4px 0;
          font-size: 13px;
          color: #ccc;
        }
        .ucb-update-current {
          color: #888 !important;
          font-size: 11px !important;
        }
        .ucb-update-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        .ucb-btn {
          padding: 8px 16px;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: opacity 0.2s, transform 0.1s;
        }
        .ucb-btn:hover {
          opacity: 0.9;
        }
        .ucb-btn:active {
          transform: scale(0.98);
        }
        .ucb-btn-primary {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }
        .ucb-btn-secondary {
          background: rgba(255,255,255,0.1);
          color: #ccc;
        }
        .ucb-btn-link {
          background: transparent;
          color: #667eea;
          text-decoration: underline;
        }
      </style>
    `;
    
    const notification = createUpdateNotification(UpdateState.updateInfo);
    popup.appendChild(notification);
    document.body.appendChild(popup);
    
    // Add event listeners
    document.getElementById('ucb-update-now').addEventListener('click', () => {
      performUpdate();
      popup.remove();
    });
    
    document.getElementById('ucb-update-later').addEventListener('click', () => {
      popup.remove();
      // Dismiss for this session
      chrome.storage.local.set({ 'updateDismissed': Date.now() });
    });
    
    document.getElementById('ucb-update-release').addEventListener('click', () => {
      chrome.tabs.create({ 
        url: UpdateState.updateInfo.url || 'https://github.com/Thexmr/UniversalChatbot/releases'
      });
    });
  }

  /**
   * Perform update (one-click)
   */
  async function performUpdate() {
    try {
      // Send message to native host
      const response = await chrome.runtime.sendMessage({
        type: 'start_update'
      });
      
      if (response && response.success) {
        showToast('🔄 Update started! Please wait...', 'info');
      } else {
        showToast('❌ Update failed. Please try manually.', 'error');
      }
    } catch (error) {
      console.error('[UCB] Update failed:', error);
      showToast('❌ Update failed. Visit GitHub to update manually.', 'error');
      
      // Fallback: open releases page
      chrome.tabs.create({ 
        url: 'https://github.com/Thexmr/UniversalChatbot/releases/latest'
      });
    }
  }

  /**
   * Show toast notification
   */
  function showToast(message, type = 'info') {
    const colors = {
      info: '#667eea',
      success: '#4CAF50',
      error: '#f44336'
    };
    
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: ${colors[type]};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 13px;
      z-index: 2147483647;
      animation: ucb-fadeIn 0.3s ease-out;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.animation = 'ucb-fadeOut 0.3s ease-out';
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }

  /**
   * Initialize update module
   */
  async function init() {
    // Load saved state
    const state = await getUpdateInfo();
    UpdateState.hasUpdate = state.hasUpdate;
    UpdateState.updateInfo = state.updateInfo;
    
    if (UpdateState.hasUpdate) {
      showUpdateBadge();
    }
    
    // Check for updates periodically
    checkForUpdates();
    setInterval(checkForUpdates, UPDATE_CHECK_INTERVAL);
    
    // Listen for messages from popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.type === 'check_update') {
        checkForUpdates().then(hasUpdate => {
          sendResponse({ hasUpdate, info: UpdateState.updateInfo });
        });
        return true; // Keep channel open
      }
      
      if (request.type === 'get_update_status') {
        sendResponse({
          hasUpdate: UpdateState.hasUpdate,
          info: UpdateState.updateInfo
        });
      }
      
      if (request.type === 'dismiss_update') {
        chrome.storage.local.set({ 'updateDismissed': Date.now() });
        UpdateState.hasUpdate = false;
        clearBadge();
        sendResponse({ success: true });
      }
    });
  }

  // Expose API
  window.UCBUpdater = {
    checkForUpdates,
    getUpdateInfo,
    showUpdatePopup,
    showUpdateBadge,
    clearBadge,
    performUpdate
  };

  // Initialize
  init();

})();