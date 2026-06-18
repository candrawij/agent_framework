import { useRef, useEffect, useCallback } from "react";
import { useChatStore } from "../stores/chatStore";
import { useSessionStore } from "../stores/sessionStore";
import { useSettingsStore } from "../stores/settingsStore";
import { ApiClient } from "../api/client";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import StatusBar from "./StatusBar";

export default function ChatWindow() {
  const {
    getMessages,
    addMessage,
    updateMessage,
    appendToMessage,
    isLoading,
    isStreaming,
    status,
    setLoading,
    setStreaming,
    setStatus,
    setError,
    setAbortController,
    stopStreaming,
  } = useChatStore();

  const { activeSessionId, createSession, updateSessionPreview } = useSessionStore();
  const { apiBaseUrl, temperature } = useSettingsStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  const didInit = useRef(false);
  // Auto-create sesi pertama saat tidak ada sesi aktif (hanya sekali)
  useEffect(() => {
    if (!didInit.current && !activeSessionId) {
      didInit.current = true;
      createSession("Sesi 1");
    }
  }, []);

  const sessionId = activeSessionId ?? "";
  const messages = getMessages(sessionId);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      const sid = sessionId;
      addMessage(sid, { role: "user", content });
      setLoading(true);
      setStreaming(false);
      setStatus("thinking");
      setError(null);

      // Placeholder pesan asisten
      const placeholder = addMessage(sid, { role: "assistant", content: "", isStreaming: true });

      const client = new ApiClient(apiBaseUrl);
      const ctrl = new AbortController();
      setAbortController(ctrl);

      const history = getMessages(sid)
        .filter((m) => m.role === "user" || (m.role === "assistant" && !m.isStreaming))
        .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
      history.push({ role: "user", content });

      await client.chatStream(history, {
        sessionId: sid,
        temperature,
        signal: ctrl.signal,
        onToken: (token) => {
          setStatus("responding");
          setStreaming(true);
          appendToMessage(sid, placeholder.id, token);
        },
        onDone: (_full, _finalSid) => {
          updateMessage(sid, placeholder.id, { isStreaming: false });
          updateSessionPreview(sid, content);
          setLoading(false);
          setStreaming(false);
          setStatus("idle");
          setAbortController(null);
        },
        onError: (err) => {
          updateMessage(sid, placeholder.id, {
            content: `❌ **Error:** ${err}`,
            isStreaming: false,
          });
          setError(err);
          setLoading(false);
          setStreaming(false);
          setStatus("error");
          setAbortController(null);
        },
      });
    },
    [sessionId, isLoading, apiBaseUrl, temperature]
  );

  const shortId = sessionId ? sessionId.slice(0, 8) : "—";

  return (
    <>
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-header-title">Chat</span>
          <StatusBar status={status} />
        </div>
        <span className="session-badge">
          {sessionId ? `# ${shortId}` : "Belum ada sesi"}
        </span>
      </div>

      {/* Messages */}
      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <svg className="chat-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            <p>Mulai percakapan baru</p>
            <p style={{ fontSize: 13, opacity: 0.5 }}>Ketik pesan di bawah untuk memulai</p>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
      </div>

      {/* Input */}
      <InputBar
        onSend={sendMessage}
        isLoading={isLoading}
        isStreaming={isStreaming}
        onStop={stopStreaming}
      />
    </>
  );
}
