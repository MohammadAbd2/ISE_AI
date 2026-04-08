import { useEffect, useRef, useState, useCallback } from "react";

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
      return "Voice recognition requires internet (Chrome/Edge use Google's servers). Please check your connection or use text input.";
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone permission blocked. Please allow microphone access in your browser settings.";
    case "no-speech":
      return "No speech detected. Please speak clearly and ensure the background is quiet.";
    case "audio-capture":
      return "No microphone found. Please connect a microphone and check system audio settings.";
    case "aborted":
      return "";
    default:
      return `Voice recognition error. Please try again or use text input.`;
  }
}

export function useVoiceInput(onTextInsert) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(null);
  const recognitionRef = useRef(null);
  const retryCountRef = useRef(0);
  const isStartingRef = useRef(false);
  const shouldListenRef = useRef(false); // Track if we should keep listening

  const checkSupport = useCallback(() => {
    if (typeof window === "undefined") {
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      return false;
    }

    // Support all browsers and platforms
    const isLocalhost = window.location.hostname === 'localhost' ||
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '0.0.0.0' ||
                       window.location.protocol === 'file:';
    const isHTTPS = window.location.protocol === 'https:';

    // All modern browsers support speech recognition on localhost/HTTPS
    return isLocalhost || isHTTPS;
  }, []);

  const requestMicPermission = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError("Your browser doesn't support microphone access.");
        return false;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());

      setPermissionGranted(true);
      return true;
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError("Microphone permission denied. Please allow microphone access in your browser settings.");
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setError("No microphone found. Please connect a microphone and try again.");
      } else {
        setError(`Microphone error: ${err.message}`);
      }
      setPermissionGranted(false);
      return false;
    }
  }, []);

  const createRecognition = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.continuous = true; // Keep listening
    recognition.interimResults = true; // Show results as you speak
    recognition.lang = "en-US";
    recognition.maxAlternatives = 3;

    return recognition;
  }, []);

  const attachRecognitionHandlers = useCallback((recognition) => {
    if (!recognition) return;

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
      setError("");
      retryCountRef.current = 0;
      isStartingRef.current = false;
    };

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript.trim();
        } else {
          interimTranscript += result[0].transcript.trim();
        }
      }

      const displayTranscript = finalTranscript || interimTranscript;
      if (displayTranscript) {
        setTranscript(displayTranscript);
      }

      if (finalTranscript) {
        onTextInsert?.(finalTranscript);
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error, event);

      if (event.error === "network") {
        retryCountRef.current += 1;

        // Only retry once, then stop
        if (retryCountRef.current === 1) {
          setError("Network error - retrying once...");
          // Stop and restart with delay
          try {
            recognition.stop();
          } catch (e) {}

          setTimeout(() => {
            if (retryCountRef.current === 1 && shouldListenRef.current) {
              try {
                // Create fresh recognition instance
                const newRecognition = createRecognition();
                if (newRecognition) {
                  recognitionRef.current = newRecognition;
                  attachRecognitionHandlers(newRecognition);
                  newRecognition.start();
                }
              } catch (e) {
                console.error("Retry failed:", e);
                setError("Voice recognition unavailable. Please check your internet connection.");
                setIsListening(false);
                isStartingRef.current = false;
                shouldListenRef.current = false;
              }
            }
          }, 1000);
          return;
        } else {
          // After retry fails, show clear message
          setError(
            "Voice recognition requires internet (uses Google's servers). " +
            "Please check your connection or use text input instead."
          );
          setIsListening(false);
          isStartingRef.current = false;
          shouldListenRef.current = false;
          return;
        }
      }

      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        requestMicPermission();
      }

      if (event.error !== "aborted") {
        const nextError = normalizeVoiceError(event.error);
        setError(nextError);
      }
      setIsListening(false);
      isStartingRef.current = false;
      shouldListenRef.current = false;
    };

    recognition.onend = () => {
      setIsListening(false);
      isStartingRef.current = false;
      
      // Only restart if we should still be listening AND no network errors occurred
      if (shouldListenRef.current && retryCountRef.current === 0) {
        try {
          recognition.start();
          setIsListening(true);
          isStartingRef.current = true;
        } catch (e) {
          // If restart fails, stop listening
          shouldListenRef.current = false;
        }
      } else if (retryCountRef.current > 0) {
        // Network error occurred, don't restart
        shouldListenRef.current = false;
      }
    };
  }, [onTextInsert, createRecognition, requestMicPermission]);

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

    // Create initial recognition instance
    const recognition = createRecognition();
    if (recognition) {
      attachRecognitionHandlers(recognition);
      recognitionRef.current = recognition;
    }

    // Listen for online/offline events
    const handleOnline = () => {
      setError(""); // Clear network error when back online
    };
    const handleOffline = () => {
      setError("You are offline. Voice recognition requires internet connection.");
      shouldListenRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setIsListening(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      shouldListenRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      recognitionRef.current = null;
    };
  }, [checkSupport, createRecognition, attachRecognitionHandlers]);

  async function startListening() {
    if (!supported || isListening || isStartingRef.current) {
      return;
    }

    setError("");
    setTranscript("");
    isStartingRef.current = true;
    shouldListenRef.current = true;

    // Check internet connectivity first
    if (!navigator.onLine) {
      setError(
        "🌐 Voice recognition requires internet connection.\n" +
        "Chrome/Edge send audio to Google's servers for processing.\n" +
        "Please connect to the internet or use text input instead."
      );
      isStartingRef.current = false;
      shouldListenRef.current = false;
      return;
    }

    const hasPermission = await requestMicPermission();
    if (!hasPermission) {
      isStartingRef.current = false;
      shouldListenRef.current = false;
      return;
    }

    try {
      retryCountRef.current = 0;

      // Create fresh recognition instance for each start
      const recognition = createRecognition();
      if (!recognition) {
        setError("Speech recognition not available in this browser.");
        isStartingRef.current = false;
        shouldListenRef.current = false;
        return;
      }

      // Stop old instance if running
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }

      // Set up new instance
      attachRecognitionHandlers(recognition);
      recognitionRef.current = recognition;

      // Start listening
      recognition.start();
    } catch (err) {
      console.error("Failed to start recognition:", err);
      isStartingRef.current = false;
      shouldListenRef.current = false;

      if (err.message?.includes("already started")) {
        // Create completely new instance
        try {
          const recognition = createRecognition();
          if (recognition) {
            attachRecognitionHandlers(recognition);
            recognitionRef.current = recognition;
            recognition.start();
          }
        } catch (retryErr) {
          setError("Failed to start voice recognition. Please refresh the page and try again.");
        }
      } else {
        setError(`Failed to start voice: ${err.message}`);
      }
    }
  }

  function stopListening() {
    shouldListenRef.current = false;
    isStartingRef.current = false;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
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

export function VoiceInputButton({ onTextInsert }) {
  const { isListening, transcript, error, supported, startListening, stopListening } =
    useVoiceInput(onTextInsert);

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

  return (
    <div className={`voice-input-wrapper ${isListening ? "listening" : ""}`}>
      <button
        type="button"
        className={`voice-button ${isListening ? "active" : ""} ${error ? "error" : ""}`}
        onClick={handleClick}
        title={
          isListening
            ? "🎙️ Click to stop listening"
            : "🎙️ Click to start voice input"
        }
        aria-label="Voice input button"
      >
        {/* Animated rings when listening */}
        {isListening && (
          <>
            <span className="voice-ring ring-1"></span>
            <span className="voice-ring ring-2"></span>
            <span className="voice-ring ring-3"></span>
          </>
        )}
        
        {/* Microphone icon with pulse animation */}
        <span className={`voice-icon-wrapper ${isListening ? "pulsing" : ""}`}>
          <svg className="voice-icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path
              fill="currentColor"
              d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
            />
            <path
              fill="currentColor"
              d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
            />
          </svg>
        </span>
        
        {/* Status indicator dot */}
        <span className={`status-dot ${isListening ? "recording" : ""}`}></span>
      </button>

      {/* Transcript tooltip */}
      {isListening && transcript && (
        <div className="transcript-tooltip">
          <div className="transcript-header">
            <span className="recording-indicator">● Recording</span>
          </div>
          <div className="transcript-text">{transcript}</div>
        </div>
      )}

      {/* Error tooltip */}
      {!isListening && error && (
        <div className="error-tooltip">
          <span className="error-icon">⚠️</span>
          <span className="error-text">
            {error.length > 50 ? error.substring(0, 50) + "..." : error}
          </span>
        </div>
      )}
    </div>
  );
}

export default useVoiceInput;
