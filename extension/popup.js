// Popup script - handles UI interactions and status updates

document.addEventListener('DOMContentLoaded', async () => {
  const enableToggle = document.getElementById('enableToggle');
  const nativeStatus = document.getElementById('nativeStatus');
  const nativeStatusText = document.getElementById('nativeStatusText');
  const reconnectBtn = document.getElementById('reconnectBtn');
  const platformToggles = document.querySelectorAll('.platform-toggle');

  // Load saved settings
  const storage = await chrome.storage.local.get(['extensionEnabled', 'enabledPlatforms']);
  
  enableToggle.checked = storage.extensionEnabled !== false;
  
  const platforms = storage.enabledPlatforms || ['web.whatsapp.com', 'web.telegram.org'];
  platformToggles.forEach(toggle => {
    toggle.checked = platforms.includes(toggle.dataset.platform);
  });

  // Check native host status
  updateNativeStatus();

  // Handle enable/disable toggle
  enableToggle.addEventListener('change', async () => {
    await chrome.storage.local.set({ extensionEnabled: enableToggle.checked });
    updateStatusText();
  });

  // Handle platform toggles
  platformToggles.forEach(toggle => {
    toggle.addEventListener('change', async () => {
      const enabled = Array.from(platformToggles)
        .filter(t => t.checked)
        .map(t => t.dataset.platform);
      await chrome.storage.local.set({ enabledPlatforms: enabled });
    });
  });

  // Handle reconnect button
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

  // Handle open dashboard button
  const openDashboardBtn = document.getElementById('openDashboardBtn');
  openDashboardBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:5000' });
  });

  // Update native host status display
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
    // Additional status updates if needed
  }
});
