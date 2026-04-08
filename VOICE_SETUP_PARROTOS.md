# Voice Recognition Setup for ParrotOS & Restricted Networks

## Problem
Voice recognition in Chrome/Chromium browsers may fail with the error:
```
"Voice recognition requires Google's speech servers, which may be blocked on this network."
```

This is because Chrome uses Google Cloud Speech API, which may be blocked on:
- ParrotOS (security-focused Linux distro)
- Corporate networks with strict firewalls
- VPN/Proxy environments
- Offline/local-only networks

## Solution 1: Configure Network Access (Recommended)

### For ParrotOS Users:

#### Step 1: Check if Google Services are Accessible
```bash
# Test connectivity to Google's speech API endpoint
curl -I https://www.google.com
curl -I https://speech.googleapis.com
```

#### Step 2: Configure Firewall (if using UFW)
```bash
# Allow HTTPS traffic required for speech API
sudo ufw allow 443/tcp
sudo ufw reload

# Verify the rule was added
sudo ufw status
```

#### Step 3: Check DNS Resolution
```bash
# Ensure DNS can resolve Google domains
nslookup speech.googleapis.com
dig speech.googleapis.com
```

#### Step 4: Browser Microphone Permissions
1. Click the 🔒 lock icon in Chrome's address bar
2. Select "Settings" or "Permissions"
3. Find "Microphone" and set to "Allow"
4. Reload the page

#### Step 5: Chrome System Audio Settings
```bash
# On Linux, ensure PulseAudio/ALSA is working
pactl info
# or
alsamixer
```

## Solution 2: Use Text Input (Immediate Alternative)
If voice doesn't work after troubleshooting:
- **Just use the text input field** - it works perfectly on all platforms
- Type your messages directly into the chat
- All AI features work identically with text

## Solution 3: Test in Incognito Mode
1. Open Chrome in Incognito Mode (Ctrl+Shift+N)
2. Navigate to the application
3. Try voice recognition
4. This bypasses browser extensions that might interfere

## Solution 4: Try Alternative Browsers
If Chrome fails, try:
- **Chromium**: `sudo apt install chromium-browser`
- **Firefox** (limited voice support on some Linux distros)
- **Brave**: `sudo apt install brave-browser`

## Troubleshooting Checklist

- [ ] Microphone is connected and working
  ```bash
  # Test microphone
  arecord -d 3 /tmp/test.wav
  aplay /tmp/test.wav
  ```

- [ ] Google services are not blocked
  ```bash
  ping google.com
  ```

- [ ] Microphone permission is granted in browser
  - Check Chrome Settings → Privacy → Site Settings → Microphone

- [ ] No VPN/Proxy is blocking Google APIs
  - Try disabling VPN temporarily to test

- [ ] Audio input device is recognized
  ```bash
  pactl list sources
  ```

- [ ] Chrome has internet access (not behind corporate proxy)
  - Test: `curl https://www.google.com`

## Voice Feature Limitations on Restricted Networks

**Chrome/Edge Speech Recognition requires:**
- ✅ Internet connectivity
- ✅ Access to Google Cloud APIs
- ✅ Microphone permission
- ❌ Not available: Fully offline/local speech recognition (requires separate ML model)

## Workaround for Fully Offline Use

If you're in a completely offline environment, we recommend:
1. **Use text input** - fully supported
2. **Local speech recognition** - would require installing additional software:
   - PocketSphinx (CMU Sphinx)
   - Kaldi
   - Other offline speech-to-text engines

To implement local speech recognition for the app, file a GitHub issue requesting this feature.

## Advanced: Proxy Configuration

If behind a corporate proxy:

### Step 1: Configure System Proxy
```bash
# For environment-wide proxy
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port
export HTTP_PROXY=http://proxy-server:port
export HTTPS_PROXY=http://proxy-server:port
```

### Step 2: Configure Chrome Proxy Settings
1. Chrome Settings → System → Open proxy settings
2. Configure proxy for your network interface
3. Add exceptions for speech.googleapis.com if needed

### Step 3: Add Proxy Bypass for Google APIs
```bash
# /etc/environment
NO_PROXY="127.0.0.1,localhost,google.com,googleapis.com,speech.googleapis.com"
```

## Still Having Issues?

### Enable Chrome Debug Logging
```bash
# Run Chrome with verbose logging
google-chrome --enable-logging --v=2 --log-level=0 2>&1 | grep -i speech
```

### Check Browser Console
1. Press F12 to open Developer Tools
2. Go to Console tab
3. Look for error messages when clicking voice button
4. Share these errors in an issue report

### Network Monitoring
```bash
# Monitor network traffic for speech API calls
sudo tcpdump -i any host google.com -w speech.pcap
wireshark speech.pcap
```

## Best Practices for ParrotOS Users

1. **Keep system updated**
   ```bash
   sudo apt update && sudo apt upgrade
   ```

2. **Use Chrome, not Chromium** (Chrome has better codec support)
   - Download from https://www.google.com/chrome/

3. **Enable microphone in ParrotOS Settings**
   - Settings → Sound → Input Device

4. **Test microphone first**
   ```bash
   # Record 3 seconds of audio
   arecord -d 3 /tmp/test.wav
   # Play it back
   aplay /tmp/test.wav
   ```

5. **Check for SELinux/AppArmor restrictions** (if applicable)
   ```bash
   # Check AppArmor status
   sudo aa-status | grep -i chrome
   ```

## Support

If voice recognition still doesn't work:
1. Use text input (fully functional alternative)
2. Report the issue with:
   - Browser version (`chrome --version`)
   - OS (`uname -a`)
   - Error message from browser console (F12)
   - Network connectivity test results

---

**Remember:** Text input works perfectly as an alternative. Voice is a convenience feature, not a requirement.
