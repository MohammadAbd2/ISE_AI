/**
 * Voice Recognition Diagnostics for ParrotOS and Restricted Networks
 * Helps users troubleshoot speech recognition issues
 */

export async function runVoiceDiagnostics() {
  const results = {
    timestamp: new Date().toISOString(),
    checks: {},
    recommendations: [],
  };

  // Check 1: Browser Support
  results.checks.browserSupport = checkBrowserSupport();

  // Check 2: Microphone Permission
  results.checks.microphonePermission = await checkMicrophonePermission();

  // Check 3: Audio Input Devices
  results.checks.audioDevices = await checkAudioDevices();

  // Check 4: Network Connectivity
  results.checks.networkConnectivity = await checkNetworkConnectivity();

  // Check 5: Speech Recognition API
  results.checks.speechApi = checkSpeechRecognitionAPI();

  // Check 6: Environment Detection
  results.checks.environment = detectEnvironment();

  // Generate recommendations
  results.recommendations = generateRecommendations(results.checks);

  return results;
}

function checkBrowserSupport() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const userAgent = navigator.userAgent;

  return {
    apiAvailable: !!SpeechRecognition,
    browser: detectBrowser(userAgent),
    userAgent,
    supported: !!SpeechRecognition,
  };
}

function detectBrowser(userAgent) {
  if (userAgent.includes("Chrome")) return "Chrome";
  if (userAgent.includes("Chromium")) return "Chromium";
  if (userAgent.includes("Edge")) return "Edge";
  if (userAgent.includes("Firefox")) return "Firefox";
  if (userAgent.includes("Safari")) return "Safari";
  return "Unknown";
}

async function checkMicrophonePermission() {
  try {
    const permissionStatus = await navigator.permissions.query({
      name: "microphone",
    });

    return {
      status: permissionStatus.state, // "granted", "denied", "prompt"
      allowed: permissionStatus.state === "granted",
      message:
        permissionStatus.state === "granted"
          ? "Microphone permission is granted"
          : permissionStatus.state === "denied"
            ? "Microphone permission is denied. Click lock icon to allow."
            : "Permission prompt will appear on first use",
    };
  } catch (err) {
    return {
      status: "unknown",
      allowed: false,
      message: "Could not check permission status",
      error: err.message,
    };
  }
}

async function checkAudioDevices() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const audioInputs = devices.filter((d) => d.kind === "audioinput");

    return {
      totalDevices: devices.length,
      audioInputDevices: audioInputs.length,
      devices: audioInputs.map((d) => ({
        label: d.label || "Unnamed microphone",
        deviceId: d.deviceId,
      })),
      available: audioInputs.length > 0,
      message:
        audioInputs.length > 0
          ? `${audioInputs.length} microphone(s) detected`
          : "No microphone detected",
    };
  } catch (err) {
    return {
      available: false,
      message: "Could not enumerate audio devices",
      error: err.message,
    };
  }
}

async function checkNetworkConnectivity() {
  const checks = {
    online: navigator.onLine,
    googleAccessible: false,
    googleSpeechAccessible: false,
    latency: null,
  };

  // Check internet connectivity
  if (!navigator.onLine) {
    return {
      ...checks,
      message: "No internet connection detected",
      available: false,
    };
  }

  // Check Google accessibility
  try {
    const startTime = performance.now();
    await fetch("https://www.google.com/generate_204", { mode: "no-cors" });
    checks.googleAccessible = true;
    checks.latency = Math.round(performance.now() - startTime);
  } catch (err) {
    checks.googleAccessible = false;
  }

  // Check speech API accessibility
  try {
    await fetch("https://speech.googleapis.com/v1", { mode: "no-cors" });
    checks.googleSpeechAccessible = true;
  } catch (err) {
    checks.googleSpeechAccessible = false;
  }

  return {
    ...checks,
    available: checks.googleAccessible,
    message: checks.googleAccessible
      ? "Network connectivity is good"
      : "Network issues detected. Check firewall/proxy settings.",
  };
}

function checkSpeechRecognitionAPI() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    return {
      available: false,
      message: "Web Speech API not supported in this browser",
    };
  }

  try {
    const recognition = new SpeechRecognition();
    const properties = {
      continuous: recognition.continuous,
      interimResults: recognition.interimResults,
      language: recognition.lang,
    };

    return {
      available: true,
      properties,
      message: "Web Speech API is available",
    };
  } catch (err) {
    return {
      available: false,
      message: "Web Speech API error",
      error: err.message,
    };
  }
}

function detectEnvironment() {
  const userAgent = navigator.userAgent.toLowerCase();
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;

  return {
    isParrotOS: userAgent.includes("parrotos"),
    isLinux: userAgent.includes("linux"),
    isLocalhost: hostname === "localhost" || hostname === "127.0.0.1",
    isHTTPS: protocol === "https:",
    isLocalFile: protocol === "file:",
    userAgent: navigator.userAgent,
    hostname,
    protocol,
    message: detectEnvironmentMessage(userAgent, hostname, protocol),
  };
}

function detectEnvironmentMessage(userAgent, hostname, protocol) {
  if (userAgent.includes("parrotos")) {
    return "ParrotOS detected - may have network restrictions on Google services";
  }
  if (userAgent.includes("linux")) {
    return "Linux detected - ensure PulseAudio/ALSA is configured";
  }
  if (hostname !== "localhost" && hostname !== "127.0.0.1" && protocol !== "https:") {
    return "Not on localhost or HTTPS - voice may not work";
  }
  return "Environment looks compatible";
}

function generateRecommendations(checks) {
  const recommendations = [];

  // Browser recommendations
  if (!checks.browserSupport?.apiAvailable) {
    recommendations.push({
      priority: "high",
      category: "Browser",
      message: "Web Speech API not available. Use Chrome, Edge, or Brave browser.",
      action: "Install a Chromium-based browser",
    });
  }

  // Microphone recommendations
  if (!checks.microphonePermission?.allowed) {
    recommendations.push({
      priority: "high",
      category: "Permission",
      message: "Microphone permission not granted",
      action: "Click the 🔒 lock icon in the address bar and allow microphone access",
    });
  }

  // Audio device recommendations
  if (!checks.audioDevices?.available) {
    recommendations.push({
      priority: "high",
      category: "Hardware",
      message: "No microphone detected",
      action: "Connect a microphone or USB audio device",
    });
  }

  // Network recommendations
  if (!checks.networkConnectivity?.available) {
    recommendations.push({
      priority: "high",
      category: "Network",
      message: "Cannot reach Google services",
      action: "Check internet connection, firewall, or proxy settings",
    });
  }

  if (!checks.networkConnectivity?.googleSpeechAccessible && checks.networkConnectivity?.available) {
    recommendations.push({
      priority: "medium",
      category: "Network",
      message: "Google Speech API may be blocked",
      action: "Check firewall settings. On ParrotOS, may need to allow Google APIs.",
    });
  }

  // Environment recommendations
  if (checks.environment?.isParrotOS) {
    recommendations.push({
      priority: "medium",
      category: "Environment",
      message: "ParrotOS may restrict Google services",
      action: "See VOICE_SETUP_PARROTOS.md for detailed setup instructions",
    });
  }

  // Fallback recommendation
  if (recommendations.length > 0) {
    recommendations.push({
      priority: "low",
      category: "Alternative",
      message: "Voice not working? Text input is fully supported",
      action: "Use text input field as an alternative",
    });
  }

  return recommendations;
}

export function formatDiagnosticsReport(diagnostics) {
  let report = "=== Voice Recognition Diagnostics ===\n\n";

  report += `Generated: ${diagnostics.timestamp}\n\n`;

  // Browser Support
  report += "Browser Support:\n";
  report += `  API Available: ${diagnostics.checks.browserSupport?.apiAvailable ? "✓" : "✗"}\n`;
  report += `  Browser: ${diagnostics.checks.browserSupport?.browser}\n\n`;

  // Microphone
  report += "Microphone:\n";
  report += `  Permission: ${diagnostics.checks.microphonePermission?.status || "unknown"}\n`;
  report += `  ${diagnostics.checks.microphonePermission?.message}\n`;
  if (diagnostics.checks.audioDevices?.devices?.length > 0) {
    report += `  Devices: ${diagnostics.checks.audioDevices.devices.map((d) => d.label).join(", ")}\n`;
  }
  report += "\n";

  // Network
  report += "Network:\n";
  report += `  Online: ${diagnostics.checks.networkConnectivity?.online ? "✓" : "✗"}\n`;
  report += `  Google Accessible: ${diagnostics.checks.networkConnectivity?.googleAccessible ? "✓" : "✗"}\n`;
  report += `  Speech API Accessible: ${diagnostics.checks.networkConnectivity?.googleSpeechAccessible ? "✓" : "✗"}\n`;
  if (diagnostics.checks.networkConnectivity?.latency) {
    report += `  Latency: ${diagnostics.checks.networkConnectivity.latency}ms\n`;
  }
  report += "\n";

  // Environment
  report += "Environment:\n";
  report += `  OS: ${diagnostics.checks.environment?.isParrotOS ? "ParrotOS" : diagnostics.checks.environment?.isLinux ? "Linux" : "Other"}\n`;
  report += `  Protocol: ${diagnostics.checks.environment?.protocol}\n`;
  report += `  ${diagnostics.checks.environment?.message}\n\n`;

  // Recommendations
  if (diagnostics.recommendations?.length > 0) {
    report += "Recommendations:\n";
    diagnostics.recommendations.forEach((rec, i) => {
      report += `\n${i + 1}. [${rec.priority.toUpperCase()}] ${rec.category}\n`;
      report += `   ${rec.message}\n`;
      report += `   → ${rec.action}\n`;
    });
  }

  return report;
}
