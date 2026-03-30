import { useEffect, useRef, useState } from "react";
import ChatLayout from "./components/ChatLayout";
import Composer from "./components/Composer";
import MessageList from "./components/MessageList";

const API_URL = "http://localhost:8000/api/chat/stream";
const MODELS_URL = "http://localhost:8000/api/models";
const CHATS_URL = "http://localhost:8000/api/chats";
const PROFILE_URL = "http://localhost:8000/api/ai/profile";
const UPLOAD_URL = "http://localhost:8000/api/files/upload";
const DEFAULT_MODEL = "llama3";
const DRAFT_SESSION_ID = "draft-chat";
const DEFAULT_EFFORT = "medium";

function createDraftContextId() {
  if (globalThis.crypto?.randomUUID) {
    return `draft:${globalThis.crypto.randomUUID()}`;
  }
  return `draft:${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      if (typeof dataUrl !== "string") {
        reject(new Error("File could not be read"));
        return;
      }
      resolve(dataUrl.split(",")[1] || "");
    };
    reader.onerror = () => reject(new Error("File upload failed"));
    reader.readAsDataURL(file);
  });
}

const initialMessages = [
  {
    role: "assistant",
    content:
      "ISE AI secure channel established. Select a model and start the session.",
  },
];

export default function App() {
  // App keeps network state, selected chat, and streaming output in one place.
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activeModel, setActiveModel] = useState(DEFAULT_MODEL);
  const [responseEffort, setResponseEffort] = useState(DEFAULT_EFFORT);
  const [models, setModels] = useState([DEFAULT_MODEL, "qwen:7b", "llama3.2:3b"]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [draftContextId, setDraftContextId] = useState(createDraftContextId);
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [customInstructions, setCustomInstructions] = useState("");
  const [memoryText, setMemoryText] = useState("");
  const [storageMode, setStorageMode] = useState("memory");
  const [profileStorageMode, setProfileStorageMode] = useState("memory");
  const [profileSaved, setProfileSaved] = useState("");
  const [error, setError] = useState("");
  const [copiedKey, setCopiedKey] = useState("");
  const abortRef = useRef(null);
  const copiedTimeoutRef = useRef(null);

  function appendSearchLog(messageIndex, log) {
    setMessages((current) =>
      current.map((message, index) => {
        if (index !== messageIndex) {
          return message;
        }
        const existingLogs = Array.isArray(message.search_logs) ? message.search_logs : [];
        const nextLogs = [...existingLogs, log];
        return { ...message, search_logs: nextLogs };
      }),
    );
  }

  async function handleStreamEvent(data, assistantIndex) {
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
    if (data.type === "search" && data.log) {
      appendSearchLog(assistantIndex, data.log);
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
    // Initial page load restores chat history and the assistant profile.
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
    setDraftContextId(createDraftContextId());
    setPendingAttachments([]);
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
      setPendingAttachments([]);
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

  async function handleUploadFiles(files) {
    setIsUploading(true);
    setError("");
    try {
      const uploaded = [];
      for (const file of files) {
        const dataBase64 = await readFileAsBase64(file);
        const response = await fetch(UPLOAD_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId || draftContextId,
            filename: file.name,
            content_type: file.type || "application/octet-stream",
            data_base64: dataBase64,
          }),
        });
        if (!response.ok) {
          let details = "Upload failed";
          try {
            const errorData = await response.json();
            details = errorData.detail || details;
          } catch {
            details = await response.text();
          }
          throw new Error(details || "Upload failed");
        }
        const data = await response.json();
        uploaded.push(data.attachment);
      }
      setPendingAttachments((current) => [...current, ...uploaded]);
    } catch (uploadError) {
      setError(uploadError.message || "File upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  function handleRemoveAttachment(attachmentId) {
    setPendingAttachments((current) =>
      current.filter((attachment) => attachment.id !== attachmentId),
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const value = input.trim();
    const requestMessage = value || "Please analyze the uploaded files.";
    if ((!value && pendingAttachments.length === 0) || isLoading || isUploading) {
      return;
    }

    const nextMessages = [
      ...messages,
      { role: "user", content: value || "Uploaded files", attachments: pendingAttachments },
    ];
    // Draft chats send local conversation context; persisted sessions reload context from the backend.
    const conversation = currentSessionId && currentSessionId !== DRAFT_SESSION_ID
      ? []
      : nextMessages.filter((message) => message.role !== "assistant" || messages.length > 1).slice(0, -1);
    setInput("");
    setIsLoading(true);
    setError("");
    const assistantIndex = nextMessages.length;
    const attachmentsForRequest = pendingAttachments;
    setPendingAttachments([]);
    setMessages([...nextMessages, { role: "assistant", content: "", search_logs: [] }]);

    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          message: requestMessage,
          model: activeModel,
          effort: responseEffort,
          attachments: attachmentsForRequest,
          conversation,
          session_id: currentSessionId || draftContextId,
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
          // The backend streams newline-delimited JSON events.
          const data = JSON.parse(line);
          await handleStreamEvent(data, assistantIndex);
        }
      }

      if (buffer.trim()) {
        const data = JSON.parse(buffer);
        await handleStreamEvent(data, assistantIndex);
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
      responseEffort={responseEffort}
      onResponseEffortChange={setResponseEffort}
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
        onUploadFiles={handleUploadFiles}
        onRemoveAttachment={handleRemoveAttachment}
        attachments={pendingAttachments}
        disabled={false}
        isLoading={isLoading}
        isUploading={isUploading}
        error={error}
      />
    </ChatLayout>
  );
}
