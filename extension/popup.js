// Popup script - handles UI interactions and status updates

document.addEventListener('DOMContentLoaded', async () => {
  const enableToggle = document.getElementById('enableToggle');
  const nativeStatus = document.getElementById('nativeStatus');
  const nativeStatusText = document.getElementById('nativeStatusText');
  const smarttaskToggle = document.getElementById('smarttaskToggle');
  const smarttaskStatus = document.getElementById('smarttaskStatus');
  const smarttaskStatusText = document.getElementById('smarttaskStatusText');
  const reconnectBtn = document.getElementById('reconnectBtn');
  const platformToggles = document.querySelectorAll('.platform-toggle');
  const currentVersionEl = document.getElementById('currentVersion');
  const checkForUpdateEl = document.getElementById('checkForUpdate');

  // Update notification elements
  const updateBanner = document.getElementById('updateBanner');
  const updateVersionEl = document.getElementById('updateVersion');
  const updateModal = document.getElementById('updateModal');
  const modalCurrentVersion = document.getElementById('modalCurrentVersion');
  const modalNewVersion = document.getElementById('modalNewVersion');
  const updateModalBody = document.getElementById('updateModalBody');
  const updateNowBtn = document.getElementById('updateNowBtn');
  const updateLaterBtn = document.getElementById('updateLaterBtn');
  const viewReleaseBtn = document.getElementById('viewReleaseBtn');

  let updateInfo = null;

  // Set current version
  const manifest = chrome.runtime.getManifest();
  currentVersionEl.textContent = manifest.version;

  // Load saved settings
  const storage = await chrome.storage.local.get([
    'extensionEnabled', 
    'enabledPlatforms',
    'hasUpdate',
    'updateInfo',
    'smarttaskEnabled'
  ]);
  
  enableToggle.checked = storage.extensionEnabled !== false;
  smarttaskToggle.checked = storage.smarttaskEnabled !== false;
  
  
  const platforms = storage.enabledPlatforms || ['web.whatsapp.com', 'web.telegram.org'];
  platformToggles.forEach(toggle => {
    toggle.checked = platforms.includes(toggle.dataset.platform);
  });

  // Check for update status
  if (storage.hasUpdate && storage.updateInfo) {
    showUpdateBanner(storage.updateInfo);
  }

  // Check native host status
  updateNativeStatus();
  
  // Check SmartTask status
  updateSmartTaskStatus();

  // Event Listeners
  enableToggle.addEventListener('change', async () => {
    await chrome.storage.local.set({ extensionEnabled: enableToggle.checked });
    updateStatusText();
  });
  
  // SmartTask toggle
  smarttaskToggle.addEventListener('change', async () => {
    await chrome.storage.local.set({ smarttaskEnabled: smarttaskToggle.checked });
    await chrome.runtime.sendMessage({
      type: 'set_smarttask_config',
      config: { enabled: smarttaskToggle.checked }
    });
    updateSmartTaskStatus();
  });

  platformToggles.forEach(toggle => {
    toggle.addEventListener('change', async () => {
      const enabled = Array.from(platformToggles)
        .filter(t => t.checked)
        .map(t => t.dataset.platform);
      await chrome.storage.local.set({ enabledPlatforms: enabled });
    });
  });

  reconnectBtn.addEventListener('click', async () => {
    nativeStatus.className = 'status-dot connecting';
    nativeStatusText.textContent = 'Reconnecting...';
    
    try {
      const response = await chrome.runtime.sendMessage({ type: 'reconnect_native' });
      if (response && response.success) {
        setTimeout(updateNativeStatus, 1000);
      }
    } catch (error) {
      console.error('Reconnect failed:', error);
      updateNativeStatus();
    }
  });

  const openDashboardBtn = document.getElementById('openDashboardBtn');
  openDashboardBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:5000' });
  });

  // Update banner click
  updateBanner.addEventListener('click', () => {
    showUpdateModal();
  });

  // Update modal actions
  updateNowBtn.addEventListener('click', async () => {
    updateNowBtn.disabled = true;
    updateNowBtn.textContent = 'Updating...';
    
    try {
      // Send message to background script to trigger update
      const response = await chrome.runtime.sendMessage({ type: 'start_update' });
      
      if (response && response.success) {
        updateModalBody.innerHTML = '<div style="color: #4CAF50;">✓ Update started! Restart the extension to apply changes.</div>';
        updateNowBtn.textContent = 'Update Started';
        
        setTimeout(() => {
          hideUpdateModal();
          hideUpdateBanner();
        }, 2000);
      } else {
        updateModalBody.innerHTML = '<div style="color: #f44336;">❌ Update failed. Please try manually from GitHub.</div>';
        updateNowBtn.textContent = 'Update Failed';
      }
    } catch (error) {
      // Fallback: open GitHub
      chrome.tabs.create({ 
        url: 'https://github.com/Thexmr/UniversalChatbot/releases/latest'
      });
    }
  });

  updateLaterBtn.addEventListener('click', () => {
    hideUpdateModal();
    chrome.storage.local.set({ updateDismissed: Date.now() });
  });

  viewReleaseBtn.addEventListener('click', () => {
    if (updateInfo && updateInfo.url) {
      chrome.tabs.create({ url: updateInfo.url });
    }
  });

  // Check for updates link
  checkForUpdateEl.addEventListener('click', async () => {
    checkForUpdateEl.textContent = 'Checking...';
    checkForUpdateEl.style.cursor = 'wait';
    
    try {
      const hasUpdate = await manualCheckForUpdates();
      if (hasUpdate) {
        checkForUpdateEl.textContent = 'Update available!';
      } else {
        checkForUpdateEl.textContent = 'No updates found';
        setTimeout(() => {
          checkForUpdateEl.textContent = 'Check for updates';
        }, 2000);
      }
    } catch (error) {
      console.error('Manual check failed:', error);
      checkForUpdateEl.textContent = 'Check failed';
      setTimeout(() => {
        checkForUpdateEl.textContent = 'Check for updates';
      }, 2000);
    } finally {
      checkForUpdateEl.style.cursor = 'pointer';
    }
  });

  // Functions
  function showUpdateBanner(info) {
    updateInfo = info;
    updateVersionEl.textContent = info.version;
    updateBanner.classList.remove('hidden');
  }

  function hideUpdateBanner() {
    updateBanner.classList.add('hidden');
  }

  function showUpdateModal() {
    if (!updateInfo) return;
    
    modalCurrentVersion.textContent = updateInfo.current || 'Current';
    modalNewVersion.textContent = 'v' + updateInfo.version;
    
    // Format release notes
    let notes = updateInfo.notes || 'Release notes not available.';
    // Simple markdown cleanup
    notes = notes.replace(/## /g, '<strong>').replace(/\n/g, '<br>');
    updateModalBody.innerHTML = notes;
    
    updateModal.classList.add('active');
  }

  function hideUpdateModal() {
    updateModal.classList.remove('active');
    updateNowBtn.disabled = false;
    updateNowBtn.textContent = 'Update Now';
  }

  async function manualCheckForUpdates() {
    try {
      const response = await fetch('https://api.github.com/repos/Thexmr/UniversalChatbot/releases/latest', {
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'UniversalChatbot-Extension'
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch');
      
      const release = await response.json();
      const latestVersion = release.tag_name.replace(/^v/, '');
      const currentVersion = manifest.version;
      
      if (isNewerVersion(latestVersion, currentVersion)) {
        const newUpdateInfo = {
          version: latestVersion,
          current: currentVersion,
          url: release.html_url,
          notes: release.body
        };
        
        // Save to storage
        await chrome.storage.local.set({
          hasUpdate: true,
          updateInfo: newUpdateInfo
        });
        
        showUpdateBanner(newUpdateInfo);
        return true;
      }
      
      return false;
      
    } catch (error) {
      console.error('Manual check failed:', error);
      throw error;
    }
  }

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

  async function updateNativeStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'get_status' });
      
      if (response && response.connected) {
        nativeStatus.className = 'status-dot';
        nativeStatusText.textContent = 'Connected to native host';
      } else {
        nativeStatus.className = 'status-dot disconnected';
        nativeStatusText.textContent = 'Disconnected from native host';
      }
    } catch (error) {
      nativeStatus.className = 'status-dot disconnected';
      nativeStatusText.textContent = 'Extension error - check installation';
    }
  }

  function updateStatusText() {
    const isEnabled = enableToggle.checked;
  }
  
  // SmartTask status check
  async function updateSmartTaskStatus() {
    try {
      const response = await fetch('http://localhost:8000/api/openclaw/webhook', {
        method: 'HEAD',
        mode: 'no-cors'
      });
      
      // If we get here or no error, SmartTask is likely running
      if (smarttaskToggle.checked) {
        smarttaskStatus.className = 'status-dot';
        smarttaskStatusText.textContent = 'Mit SmartTask verbunden';
      } else {
        smarttaskStatus.className = 'status-dot disconnected';
        smarttaskStatusText.textContent = 'SmartTask Integration deaktiviert';
      }
    } catch (error) {
      smarttaskStatus.className = 'status-dot disconnected';
      if (smarttaskToggle.checked) {
        smarttaskStatusText.textContent = 'SmartTask nicht erreichbar (localhost:8000)';
      } else {
        smarttaskStatusText.textContent = 'SmartTask Integration deaktiviert';
      }
      console.log('[UCB] SmartTask status check:', error.message);
    }
  }
});