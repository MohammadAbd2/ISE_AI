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
      return "Network error: Speech recognition requires an active internet connection. Please check your connection and try again.";
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone permission blocked. Click the 🔒 icon in your browser's address bar and allow microphone access.";
    case "no-speech":
      return "No speech detected. Please speak clearly and closer to your microphone.";
    case "audio-capture":
      return "No microphone found. Please connect a microphone and refresh the page.";
    case "aborted":
      return "";
    default:
      return `Voice error (${errorCode}). Please try again or use text input.`;
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

  const checkSupport = useCallback(() => {
    if (typeof window === "undefined") {
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      return false;
    }

    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.protocol === 'file:';
    const isHTTPS = window.location.protocol === 'https:';

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
        onTextInsert?.(nextTranscript);
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
        } catch (e) {}
      }
      recognitionRef.current = null;
    };
  }, [onTextInsert, checkSupport, requestMicPermission]);

  async function startListening() {
    if (!recognitionRef.current || !supported || isListening) {
      return;
    }

    setError("");
    setTranscript("");

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
      try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = "en-US";
        recognitionRef.current.maxAlternatives = 1;
        
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
        onTextInsert?.(nextTranscript);
        setIsListening(false);
      }
    };

    recognitionRef.current.onerror = (event) => {
      console.error("Speech recognition error:", event.error, event);
      
      if (event.error === "network") {
        retryCountRef.current += 1;
        
        if (retryCountRef.current <= 2) {
          setError(`Network error - retrying (${retryCountRef.current}/2)...`);
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
            } catch (e) {}
          }, 1000);
          return;
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
    <div className={`voice-input-container ${isListening ? "listening" : ""}`}>
      <button
        type="button"
        className={`voice-input-button ${isListening ? "active" : ""}`}
        onClick={handleClick}
        title={
          isListening 
            ? "Click to stop listening (🎙️)" 
            : "Click to start voice input (🎙️)"
        }
        aria-label="Voice input button"
      >
        <span className="voice-icon">🎙️</span>
        <span className="voice-label">
          {isListening ? "Listening..." : "Voice"}
        </span>
      </button>
      
      {isListening && transcript ? (
        <div className="voice-transcript">
          <div className="voice-indicator">●</div>
          <div className="voice-text">{transcript}</div>
        </div>
      ) : null}
      
      {!isListening && error ? (
        <div className="voice-error" title={error}>
          {error.length > 60 ? error.substring(0, 60) + "..." : error}
        </div>
      ) : null}
    </div>
  );
}

export default useVoiceInput;
