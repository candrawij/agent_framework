import { useRef, KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (text: string) => void;
  isLoading: boolean;
  isStreaming: boolean;
  onStop: () => void;
}

export default function InputBar({ onSend, isLoading, isStreaming, onStop }: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const text = inputRef.current?.value.trim() ?? "";
    if (!text || isLoading) return;
    onSend(text);
    if (inputRef.current) {
      inputRef.current.value = "";
      inputRef.current.style.height = "44px";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "44px";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const isActive = isLoading || isStreaming;

  return (
    <div className="chat-input-bar">
      <textarea
        ref={inputRef}
        className="chat-input"
        placeholder={isActive ? "Model sedang memproses..." : "Ketik pesan... (Enter kirim, Shift+Enter baris baru)"}
        rows={1}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={isActive}
      />

      {isStreaming ? (
        <button
          className="stop-btn"
          onClick={onStop}
          title="Hentikan streaming"
        >
          <Square size={18} fill="currentColor" />
        </button>
      ) : (
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={isLoading}
          title="Kirim pesan"
        >
          {isLoading ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="spin">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
          ) : (
            <Send size={18} />
          )}
        </button>
      )}
    </div>
  );
}
