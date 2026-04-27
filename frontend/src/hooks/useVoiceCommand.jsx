import { useEffect, useRef, useState, useCallback } from "react";
import { runVoiceDiagnostics, formatDiagnosticsReport } from "../utils/voiceDiagnostics";

function classifyTranscript(transcript) {
  const lower = transcript.toLowerCase();
  const extract = (pattern) => {
    const match = lower.match(pattern);
    return match ? match[1] : "";
  };

  if (/(dashboard|tools|features)/.test(lower)) {
    return { transcript, command_type: "navigate", action: "dashboard", suggested_params: {} };
  }
  if (/(chat|conversation|message)/.test(lower)) {
    return { transcript, command_type: "navigate", action: "chat", suggested_params: {} };
  }
  if (/(search|find|lookup)/.test(lower)) {
    return {
      transcript,
      command_type: "search",
      action: "rag_search",
      suggested_params: { query: extract(/(?:search|find|lookup)(?: for)?\s+(.+)/) || transcript },
    };
  }
  if (/(run|execute|test)/.test(lower)) {
    return {
      transcript,
      command_type: "run",
      action: "terminal",
      suggested_params: { command: extract(/(?:run|execute|test)\s+(.+)/) || transcript },
    };
  }
  return { transcript, command_type: "message", action: "compose", suggested_params: {} };
}

function normalizeVoiceError(errorCode) {
  switch (errorCode) {
    case "network":
      return "Network error: Speech recognition requires internet access. On restricted networks (ParrotOS, VPNs), try: 1) Allow microphone permission, 2) Check firewall settings, 3) Try a different browser, or 4) Use text input.";
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone permission blocked. Click the 🔒 icon in the address bar and select 'Allow' for microphone access.";
    case "no-speech":
      return "No speech detected. Please speak clearly, closer to the microphone, and ensure the background is quiet.";
    case "audio-capture":
      return "No microphone found. Please connect a microphone, check system audio settings, and refresh the page.";
    case "aborted":
      return "";
    case "service-not-allowed-permission":
      return "Speech service not available. Check browser settings: Settings → Privacy → Site Settings → Microphone → Allow.";
    default:
      return `Voice error (${errorCode}). If this persists on a restricted network, please use text input.`;
  }
}

export function useVoiceCommand(onCommand) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(null);
  const recognitionRef = useRef(null);
  const retryCountRef = useRef(0);

  // Check browser support
  const checkSupport = useCallback(() => {
    if (typeof window === "undefined") {
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      return false;
    }

    // Check if we're on localhost or HTTPS
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.protocol === 'file:';
    const isHTTPS = window.location.protocol === 'https:';

    return isLocalhost || isHTTPS;
  }, []);

  // Request microphone permission
  const requestMicPermission = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError("Your browser doesn't support microphone access.");
        return false;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Stop the stream immediately - we just needed permission
      stream.getTracks().forEach(track => track.stop());
      
      setPermissionGranted(true);
      return true;
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError("Microphone permission denied. Please click the 🔒 icon in your browser's address bar and allow microphone access.");
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setError("No microphone found. Please connect a microphone and try again.");
      } else {
        setError(`Microphone error: ${err.message}`);
      }
      setPermissionGranted(false);
      return false;
    }
  }, []);

  // Initialize speech recognition
  useEffect(() => {
    const isSupported = checkSupport();
    setSupported(isSupported);

    if (!isSupported) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setError("Voice input requires Chrome, Edge, or Safari. Your browser doesn't support speech recognition.");
      } else {
        setError("Voice input requires HTTPS or localhost. Please use a secure connection.");
      }
      return undefined;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
      setError("");
      retryCountRef.current = 0;
    };

    recognition.onresult = (event) => {
      const result = event.results[event.resultIndex];
      const nextTranscript = result[0].transcript.trim();
      setTranscript(nextTranscript);
      
      if (result.isFinal && nextTranscript) {
        const payload = classifyTranscript(nextTranscript);
        onCommand?.(payload);
        setIsListening(false);
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      
      if (event.error === "not-allowed") {
        requestMicPermission();
      }
      
      const nextError = normalizeVoiceError(event.error);
      setError(nextError);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore stop errors
        }
      }
      recognitionRef.current = null;
    };
  }, [onCommand, checkSupport, requestMicPermission]);

  async function startListening() {
    if (!recognitionRef.current || !supported || isListening) {
      return;
    }

    setError("");
    setTranscript("");

    // Request permission first
    const hasPermission = await requestMicPermission();
    if (!hasPermission) {
      return;
    }

    try {
      retryCountRef.current = 0;
      recognitionRef.current.start();
    } catch (err) {
      console.error("Failed to start recognition:", err);
      handleStartError(err);
    }
  }

  function handleStartError(err) {
    if (err.message?.includes("already started")) {
      // Reset the recognition object and retry
      try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = "en-US";
        recognitionRef.current.maxAlternatives = 1;
        
        // Re-attach event handlers
        attachRecognitionHandlers();
        
        recognitionRef.current.start();
      } catch (retryErr) {
        setError("Failed to start voice recognition. Please refresh the page and try again.");
      }
    } else {
      setError(`Failed to start voice: ${err.message}`);
    }
  }

  function attachRecognitionHandlers() {
    if (!recognitionRef.current) return;
    
    recognitionRef.current.onstart = () => {
      setIsListening(true);
      setTranscript("");
      setError("");
      retryCountRef.current = 0;
    };

    recognitionRef.current.onresult = (event) => {
      const result = event.results[event.resultIndex];
      const nextTranscript = result[0].transcript.trim();
      setTranscript(nextTranscript);
      
      if (result.isFinal && nextTranscript) {
        const payload = classifyTranscript(nextTranscript);
        onCommand?.(payload);
        setIsListening(false);
      }
    };

    recognitionRef.current.onerror = (event) => {
      console.error("Speech recognition error:", event.error, event);
      
      // Handle network errors with retry
      if (event.error === "network") {
        retryCountRef.current += 1;
        
        // For restricted networks (ParrotOS), provide user guidance
        const isRestrictedNetwork = () => {
          // ParrotOS and other restricted envs often block Google services
          return navigator.userAgent.includes("ParrotOS") || 
                 navigator.userAgent.includes("Linux") ||
                 window.location.hostname === "localhost";
        };
        
        if (retryCountRef.current <= 2 && !isRestrictedNetwork()) {
          setError(`Network error - retrying (${retryCountRef.current}/2)...`);
          // Auto-retry after 1 second
          setTimeout(() => {
            try {
              recognitionRef.current.stop();
              setTimeout(() => {
                try {
                  recognitionRef.current.start();
                } catch (e) {
                  setError("Voice recognition unavailable. Please check your internet connection and try again.");
                  setIsListening(false);
                }
              }, 500);
            } catch (e) {
              // Ignore stop errors
            }
          }, 1000);
          return;
        } else {
          // On restricted networks, provide actionable guidance
          if (isRestrictedNetwork()) {
            setError(
              "Voice recognition requires Google's speech servers, which may be blocked on this network.\n\n" +
              "Solutions:\n" +
              "1. Check if Google services are accessible: https://www.google.com\n" +
              "2. Disable VPN or proxy if active\n" +
              "3. Check firewall settings to allow Google Cloud Speech API\n" +
              "4. Use text input as an alternative\n\n" +
              "For offline speech-to-text, we recommend using text input."
            );
          } else {
            setError(
              "Voice recognition requires an active internet connection.\n\n" +
              "Chrome/Edge use Google's speech servers which are currently unreachable.\n\n" +
              "Please:\n" +
              "1. Check your internet connection\n" +
              "2. Ensure you're not behind a restrictive firewall\n" +
              "3. Try again in a moment\n\n" +
              "Or use text input instead."
            );
          }
          setIsListening(false);
          return;
        }
      }
      
      if (event.error === "not-allowed") {
        requestMicPermission();
      }
      
      const nextError = normalizeVoiceError(event.error);
      setError(nextError);
      setIsListening(false);
    };

    recognitionRef.current.onend = () => {
      setIsListening(false);
    };
  }

  function stopListening() {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // Ignore stop errors
      }
    }
    setIsListening(false);
  }

  return {
    isListening,
    transcript,
    error,
    supported,
    startListening,
    stopListening,
  };
}

export function VoiceCommandButton({ onCommand }) {
  const { isListening, transcript, error, supported, startListening, stopListening } =
    useVoiceCommand(onCommand);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [diagnosticsReport, setDiagnosticsReport] = useState(null);

  // Hide button entirely if not supported
  if (!supported) {
    return null;
  }

  const handleClick = async () => {
    if (isListening) {
      stopListening();
    } else {
      await startListening();
    }
  };

  const handleRunDiagnostics = async () => {
    const diagnostics = await runVoiceDiagnostics();
    setDiagnosticsReport(diagnostics);
    setShowDiagnostics(true);
  };

  const closeDiagnostics = () => {
    setShowDiagnostics(false);
  };

  return (
    <div className={`voice-command ${isListening ? "active" : ""}`}>
      <button
        type="button"
        className="voice-button"
        onClick={handleClick}
        title={
          isListening 
            ? "Click to stop listening" 
            : "Click to start voice input"
        }
      >
        <span className="voice-button-dot" />
        <span className="voice-button-label">
          {isListening ? "Listening..." : "Voice"}
        </span>
      </button>
      {isListening && transcript ? (
        <span className="voice-live-text">
          <span className="voice-live-indicator">●</span>
          {transcript}
        </span>
      ) : null}
      {!isListening && error ? (
        <div className="voice-error-container">
          <span className="voice-error" title={error}>
            {error.length > 50 ? error.substring(0, 50) + "..." : error}
          </span>
          <button
            type="button"
            className="voice-diagnose-button"
            onClick={handleRunDiagnostics}
            title="Run voice diagnostics to troubleshoot"
          >
            🔧
          </button>
          {showDiagnostics && diagnosticsReport && (
            <VoiceDiagnosticsModal 
              diagnostics={diagnosticsReport} 
              onClose={closeDiagnostics}
            />
          )}
        </div>
      ) : null}
    </div>
  );
}

function VoiceDiagnosticsModal({ diagnostics, onClose }) {
  const reportText = formatDiagnosticsReport(diagnostics);

  return (
    <div className="voice-diagnostics-overlay" onClick={onClose}>
      <div className="voice-diagnostics-modal" onClick={(e) => e.stopPropagation()}>
        <div className="voice-diagnostics-header">
          <h3>Voice Recognition Diagnostics</h3>
          <button 
            type="button"
            className="voice-diagnostics-close"
            onClick={onClose}
            title="Close diagnostics"
          >
            ✕
          </button>
        </div>
        
        <div className="voice-diagnostics-content">
          <div className="diagnostics-section">
            <h4>Browser Support</h4>
            <p className={diagnostics.checks.browserSupport?.apiAvailable ? "status-ok" : "status-error"}>
              API Available: {diagnostics.checks.browserSupport?.apiAvailable ? "✓" : "✗"}
            </p>
            <p>Browser: {diagnostics.checks.browserSupport?.browser}</p>
          </div>

          <div className="diagnostics-section">
            <h4>Microphone</h4>
            <p className={diagnostics.checks.microphonePermission?.allowed ? "status-ok" : "status-error"}>
              Permission: {diagnostics.checks.microphonePermission?.status}
            </p>
            <p>{diagnostics.checks.microphonePermission?.message}</p>
            {diagnostics.checks.audioDevices?.devices?.length > 0 && (
              <p>Devices: {diagnostics.checks.audioDevices.devices.map(d => d.label).join(", ")}</p>
            )}
          </div>

          <div className="diagnostics-section">
            <h4>Network</h4>
            <p className={diagnostics.checks.networkConnectivity?.available ? "status-ok" : "status-error"}>
              Online: {diagnostics.checks.networkConnectivity?.online ? "✓" : "✗"}
            </p>
            <p>Google Accessible: {diagnostics.checks.networkConnectivity?.googleAccessible ? "✓" : "✗"}</p>
            <p>Speech API: {diagnostics.checks.networkConnectivity?.googleSpeechAccessible ? "✓" : "✗"}</p>
            {diagnostics.checks.networkConnectivity?.latency && (
              <p>Latency: {diagnostics.checks.networkConnectivity.latency}ms</p>
            )}
          </div>

          <div className="diagnostics-section">
            <h4>Environment</h4>
            <p>{diagnostics.checks.environment?.message}</p>
            <p>OS: {diagnostics.checks.environment?.isParrotOS ? "ParrotOS" : 
                    diagnostics.checks.environment?.isLinux ? "Linux" : "Other"}</p>
          </div>

          {diagnostics.recommendations?.length > 0 && (
            <div className="diagnostics-section recommendations">
              <h4>Recommendations</h4>
              {diagnostics.recommendations.map((rec, i) => (
                <div key={i} className={`recommendation priority-${rec.priority}`}>
                  <strong>[{rec.priority.toUpperCase()}] {rec.category}</strong>
                  <p>{rec.message}</p>
                  <p className="action">→ {rec.action}</p>
                </div>
              ))}
            </div>
          )}

          <div className="diagnostics-section">
            <h4>Full Report</h4>
            <pre className="diagnostics-report">{reportText}</pre>
            <button
              type="button"
              className="copy-report-button"
              onClick={() => {
                navigator.clipboard.writeText(reportText);
              }}
            >
              📋 Copy Report
            </button>
          </div>
        </div>

        <div className="voice-diagnostics-footer">
          <p>See <strong>VOICE_SETUP_PARROTOS.md</strong> in the project root for detailed setup instructions.</p>
          <button
            type="button"
            className="voice-diagnostics-ok"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default useVoiceCommand;
