import { useEffect, useRef, useState } from "react";

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
      return "Voice capture is unavailable in this browser session.";
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone permission is blocked in this browser.";
    case "no-speech":
      return "No speech was detected.";
    case "audio-capture":
      return "No microphone was found.";
    case "aborted":
      return "";
    default:
      return "Voice recognition failed. Try again or use text input.";
  }
}

export function useVoiceCommand(onCommand) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      setSupported(false);
      return undefined;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      setError("Voice input is supported in Chrome and Edge.");
      return undefined;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
      setError("");
    };

    recognition.onresult = (event) => {
      const result = event.results[event.resultIndex];
      const nextTranscript = result[0].transcript.trim();
      setTranscript(nextTranscript);
      if (result.isFinal && nextTranscript) {
        const payload = classifyTranscript(nextTranscript);
        onCommand?.(payload);
      }
    };

    recognition.onerror = (event) => {
      const nextError = normalizeVoiceError(event.error);
      setError(nextError);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    return () => {
      recognition.stop();
      recognitionRef.current = null;
    };
  }, [onCommand]);

  function startListening() {
    if (!recognitionRef.current || !supported || isListening) {
      return;
    }
    setError("");
    setTranscript("");
    try {
      recognitionRef.current.start();
    } catch {
      setError("Microphone is already active.");
    }
  }

  function stopListening() {
    recognitionRef.current?.stop();
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

  return (
    <div className={`voice-command ${isListening ? "active" : ""}`}>
      <button
        type="button"
        className="voice-button"
        disabled={!supported}
        onClick={isListening ? stopListening : startListening}
        title={supported ? "Voice input" : "Voice input unavailable"}
      >
        <span className="voice-button-dot" />
        <span className="voice-button-label">{isListening ? "Listening" : "Voice"}</span>
      </button>
      {isListening && transcript ? <span className="voice-live-text">{transcript}</span> : null}
      {!isListening && error ? <span className="voice-error" title={error}>Voice unavailable</span> : null}
    </div>
  );
}

export default useVoiceCommand;
