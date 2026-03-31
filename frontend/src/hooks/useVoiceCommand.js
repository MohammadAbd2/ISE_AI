import { useState, useEffect, useRef } from "react";

/**
 * Voice Command Hook
 * 
 * Provides speech recognition and command processing.
 */
export function useVoiceCommand() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState(null);
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setSupported(false);
      setError("Voice commands not supported in this browser. Use Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      const current = event.resultIndex;
      const result = event.results[current];
      const transcript = result[0].transcript;
      setTranscript(transcript);

      if (result.isFinal) {
        processVoiceCommand(transcript);
      }
    };

    recognition.onerror = (event) => {
      setError(`Voice error: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const processVoiceCommand = async (transcript) => {
    try {
      const response = await fetch("http://localhost:8000/api/voice/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript }),
      });

      if (!response.ok) throw new Error("Failed to process voice command");

      const data = await response.json();
      
      // Dispatch custom event with command data
      window.dispatchEvent(new CustomEvent("voice-command", { detail: data }));
      
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    }
  };

  const startListening = () => {
    if (recognitionRef.current && supported) {
      setTranscript("");
      setError(null);
      recognitionRef.current.start();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  return {
    isListening,
    transcript,
    error,
    supported,
    startListening,
    stopListening,
  };
}

/**
 * Voice Command Button Component
 */
export function VoiceCommandButton({ onCommand }) {
  const { isListening, transcript, error, supported, startListening, stopListening } = useVoiceCommand();

  if (!supported) {
    return (
      <button
        type="button"
        className="voice-button disabled"
        disabled
        title="Voice commands not supported"
      >
        🎤
      </button>
    );
  }

  return (
    <div className="voice-command-container">
      <button
        type="button"
        className={`voice-button ${isListening ? "listening" : ""}`}
        onClick={isListening ? stopListening : startListening}
        title={isListening ? "Stop listening" : "Start voice command"}
      >
        {isListening ? "🔴" : "🎤"}
      </button>
      
      {isListening && (
        <div className="voice-transcript">
          <span className="voice-indicator">Listening...</span>
          {transcript && <span className="voice-text">{transcript}</span>}
        </div>
      )}
      
      {error && <span className="voice-error">{error}</span>}
    </div>
  );
}

export default useVoiceCommand;
