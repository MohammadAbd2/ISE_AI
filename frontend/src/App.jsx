import { useEffect, useRef, useState } from "react";
import ChatLayout from "./components/ChatLayout";
import Composer from "./components/Composer";
import MessageList from "./components/MessageList";

const API_URL = "http://localhost:8000/api/chat/stream";
const MODELS_URL = "http://localhost:8000/api/models";
const CHATS_URL = "http://localhost:8000/api/chats";
const PROFILE_URL = "http://localhost:8000/api/ai/profile";
const DEFAULT_MODEL = "llama3";
const DRAFT_SESSION_ID = "draft-chat";

const initialMessages = [
  {
    role: "assistant",
    content:
      "ISE AI secure channel established. Select a model and start the session.",
  },
];

export default function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeModel, setActiveModel] = useState(DEFAULT_MODEL);
  const [models, setModels] = useState([DEFAULT_MODEL, "qwen:7b", "llama3.2:3b"]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [customInstructions, setCustomInstructions] = useState("");
  const [memoryText, setMemoryText] = useState("");
  const [storageMode, setStorageMode] = useState("memory");
  const [profileStorageMode, setProfileStorageMode] = useState("memory");
  const [profileSaved, setProfileSaved] = useState("");
  const [error, setError] = useState("");
  const [copiedKey, setCopiedKey] = useState("");
  const abortRef = useRef(null);
  const copiedTimeoutRef = useRef(null);

  useEffect(() => {
    async function loadModels() {
      try {
        const response = await fetch(MODELS_URL);
        if (!response.ok) {
          throw new Error("Failed to load models");
        }
        const data = await response.json();
        if (Array.isArray(data.models) && data.models.length > 0) {
          setModels(data.models);
          if (!data.models.includes(activeModel)) {
            setActiveModel(data.models[0]);
          }
        }
      } catch {
        setModels((current) => Array.from(new Set(current)));
      }
    }

    loadModels();
  }, []);

  useEffect(() => {
    loadSessions();
    loadProfile();
  }, []);

  useEffect(() => {
    return () => {
      copiedTimeoutRef.current && clearTimeout(copiedTimeoutRef.current);
      abortRef.current?.abort();
    };
  }, []);

  function stopGeneration() {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
  }

  function resetChat() {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages(initialMessages);
    setCurrentSessionId(null);
    setInput("");
    setError("");
    setIsLoading(false);
    setCopiedKey("");
  }

  async function loadSessions() {
    try {
      const response = await fetch(CHATS_URL);
      if (!response.ok) {
        throw new Error("Failed to load chats");
      }
      const data = await response.json();
      setSessions(Array.isArray(data.sessions) ? data.sessions : []);
      setStorageMode(data.storage_mode || "memory");
    } catch {
      setSessions([]);
    }
  }

  async function loadProfile() {
    try {
      const response = await fetch(PROFILE_URL);
      if (!response.ok) {
        throw new Error("Failed to load profile");
      }
      const data = await response.json();
      setCustomInstructions(data.custom_instructions || "");
      setMemoryText(data.memory || "");
      setProfileStorageMode(data.storage_mode || "memory");
    } catch {
      setProfileStorageMode("memory");
    }
  }

  async function openSession(sessionId) {
    if (sessionId === DRAFT_SESSION_ID) {
      resetChat();
      return;
    }
    try {
      const response = await fetch(`${CHATS_URL}/${sessionId}`);
      if (!response.ok) {
        throw new Error("Failed to load chat");
      }
      const data = await response.json();
      setCurrentSessionId(data.id);
      setActiveModel(data.model || DEFAULT_MODEL);
      setMessages(data.messages.length > 0 ? data.messages : initialMessages);
      setError("");
    } catch {
      setError("Failed to load chat history.");
    }
  }

  async function deleteSession(sessionId) {
    if (sessionId === DRAFT_SESSION_ID) {
      return;
    }
    try {
      const response = await fetch(`${CHATS_URL}/${sessionId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete chat");
      }
      if (sessionId === currentSessionId) {
        resetChat();
      }
      await loadSessions();
    } catch {
      setError("Failed to delete chat.");
    }
  }

  async function clearHistory() {
    try {
      const response = await fetch(CHATS_URL, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to clear history");
      }
      resetChat();
      setSessions([]);
    } catch {
      setError("Failed to clear chat history.");
    }
  }

  async function saveProfile() {
    try {
      const response = await fetch(PROFILE_URL, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          custom_instructions: customInstructions,
          memory: memoryText,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to save profile");
      }
      const data = await response.json();
      setCustomInstructions(data.custom_instructions || "");
      setMemoryText(data.memory || "");
      setProfileStorageMode(data.storage_mode || "memory");
      setProfileSaved("Saved");
      setTimeout(() => setProfileSaved(""), 1600);
    } catch {
      setError("Failed to save AI profile.");
    }
  }

  async function handleCopyMessage(message, index) {
    const key = `${message.role}-${index}`;
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedKey(key);
      copiedTimeoutRef.current && clearTimeout(copiedTimeoutRef.current);
      copiedTimeoutRef.current = setTimeout(() => setCopiedKey(""), 1600);
    } catch {
      setError("Copy failed. Clipboard access is blocked in this browser.");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const value = input.trim();
    if (!value || isLoading) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: value }];
    const conversation = currentSessionId && currentSessionId !== DRAFT_SESSION_ID
      ? []
      : nextMessages.filter((message) => message.role !== "assistant" || messages.length > 1).slice(0, -1);
    setInput("");
    setIsLoading(true);
    setError("");
    const assistantIndex = nextMessages.length;
    setMessages([...nextMessages, { role: "assistant", content: "" }]);

    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          message: value,
          model: activeModel,
          conversation,
          session_id: currentSessionId && currentSessionId !== DRAFT_SESSION_ID ? currentSessionId : null,
        }),
      });

      if (!response.ok) {
        throw new Error("Backend request failed");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      if (!reader) {
        throw new Error("Streaming is not available");
      }

      while (true) {
        const { value: chunk, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }
          const data = JSON.parse(line);
          if (data.type === "meta" && data.model) {
            setActiveModel(data.model);
          }
          if (data.type === "meta" && data.session_id) {
            setCurrentSessionId(data.session_id);
          }
          if (data.type === "meta" && data.storage_mode) {
            setStorageMode(data.storage_mode);
          }
          if (data.type === "meta" && data.profile_storage_mode) {
            setProfileStorageMode(data.profile_storage_mode);
          }
          if (data.type === "token") {
            setMessages((current) =>
              current.map((message, index) =>
                index === assistantIndex
                  ? { ...message, content: message.content + data.content }
                  : message,
              ),
            );
          }
          if (data.type === "error") {
            throw new Error(data.message || "Streaming failed");
          }
          if (data.type === "done") {
            await loadSessions();
            await loadProfile();
          }
        }
      }

      if (buffer.trim()) {
        const data = JSON.parse(buffer);
        if (data.type === "meta" && data.model) {
          setActiveModel(data.model);
        }
        if (data.type === "meta" && data.session_id) {
          setCurrentSessionId(data.session_id);
        }
        if (data.type === "meta" && data.storage_mode) {
          setStorageMode(data.storage_mode);
        }
        if (data.type === "meta" && data.profile_storage_mode) {
          setProfileStorageMode(data.profile_storage_mode);
        }
        if (data.type === "token") {
          setMessages((current) =>
            current.map((message, index) =>
              index === assistantIndex
                ? { ...message, content: message.content + data.content }
                : message,
            ),
          );
        }
      }
    } catch (requestError) {
      const aborted = requestError.name === "AbortError";
      if (aborted) {
        setMessages((current) =>
          current.map((message, index) =>
            index === assistantIndex && !message.content.trim()
              ? { ...message, content: "Generation stopped." }
              : message,
          ),
        );
      } else {
        setError(
          "The backend is unavailable. Start FastAPI and Ollama, then try again.",
        );
        setMessages((current) =>
          current.map((message, index) =>
            index === assistantIndex
              ? {
                  ...message,
                  content:
                    "I could not reach the backend service. Verify that FastAPI is running on port 8000 and Ollama is available locally.",
                }
              : message,
          ),
        );
      }
    } finally {
      abortRef.current = null;
      setIsLoading(false);
      await loadSessions();
      await loadProfile();
    }
  }

  const displayedSessions = currentSessionId === null || currentSessionId === DRAFT_SESSION_ID
    ? [
        {
          id: DRAFT_SESSION_ID,
          title: "New chat",
          preview: "Draft session",
        },
        ...sessions,
      ]
    : sessions;

  return (
    <ChatLayout
      activeModel={activeModel}
      models={models}
      onModelChange={setActiveModel}
      sessions={displayedSessions}
      currentSessionId={currentSessionId || DRAFT_SESSION_ID}
      messageCount={messages.length}
      onResetChat={resetChat}
      onOpenSession={openSession}
      onDeleteSession={deleteSession}
      onClearHistory={clearHistory}
      customInstructions={customInstructions}
      memoryText={memoryText}
      onCustomInstructionsChange={setCustomInstructions}
      onMemoryTextChange={setMemoryText}
      onSaveProfile={saveProfile}
      profileSaved={profileSaved}
      storageMode={storageMode}
      profileStorageMode={profileStorageMode}
    >
      <MessageList
        messages={messages}
        isLoading={isLoading}
        copiedKey={copiedKey}
        onCopyMessage={handleCopyMessage}
      />
      <Composer
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        onStop={stopGeneration}
        disabled={false}
        isLoading={isLoading}
        error={error}
      />
    </ChatLayout>
  );
}
