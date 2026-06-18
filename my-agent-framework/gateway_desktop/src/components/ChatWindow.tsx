import { useRef, useEffect } from "react";
import { useChatStore } from "../stores/chatStore";
import { useSettingsStore } from "../stores/settingsStore";
import { ApiClient } from "../api/client";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";

export default function ChatWindow() {
  const { messages, addMessage, updateMessage, isLoading, setLoading, setError, setSessionId, sessionId } =
    useChatStore();
  const { apiBaseUrl, temperature } = useSettingsStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    addMessage({ role: "user", content });
    setLoading(true);
    setError(null);

    const placeholder = addMessage({ role: "assistant", content: "", isStreaming: true });
    const client = new ApiClient(apiBaseUrl);

    try {
      const history = messages
        .filter((m) => m.role === "user" || (m.role === "assistant" && !m.isStreaming))
        .map((m) => ({ role: m.role, content: m.content }));
      history.push({ role: "user", content });

      const resp = await client.chat(history, { sessionId: sessionId ?? undefined, temperature });
      setSessionId(resp.session_id);
      updateMessage(placeholder.id, { content: resp.content, isStreaming: false });
    } catch (e: any) {
      updateMessage(placeholder.id, {
        content: `❌ Error: ${e.message}`,
        isStreaming: false,
      });
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="chat-header">
        <span className="chat-header-title">Chat</span>
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
          {sessionId ? `Session: ${sessionId}` : "No session"}
        </span>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <svg className="chat-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            <p>Mulai percakapan baru</p>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
      </div>

      <InputBar onSend={sendMessage} isLoading={isLoading} />
    </>
  );
}
