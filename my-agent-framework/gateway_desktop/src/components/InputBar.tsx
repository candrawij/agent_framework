import { useRef, KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSend, isLoading }: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const text = inputRef.current?.value.trim() ?? "";
    if (!text || isLoading) return;
    onSend(text);
    if (inputRef.current) inputRef.current.value = "";
    inputRef.current?.style.setProperty("height", "44px");
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

  return (
    <div className="chat-input-bar">
      <textarea
        ref={inputRef}
        className="chat-input"
        placeholder="Ketik pesan... (Enter untuk kirim, Shift+Enter untuk baris baru)"
        rows={1}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={isLoading}
      />
      <button className="send-btn" onClick={handleSend} disabled={isLoading} title="Kirim">
        {isLoading ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        )}
      </button>
    </div>
  );
}
