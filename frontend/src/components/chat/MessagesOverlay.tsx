import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { COPY } from "../../lib/cardCopy";
import { truncateUrlMiddle } from "../../lib/urlDisplay";

export interface ChatMessage {
  role: "user" | "agent";
  content: string;
}

export function UserUrlBubble({ url }: { url: string }) {
  const [expanded, setExpanded] = useState(url.length <= 50);
  const display = expanded ? url : truncateUrlMiddle(url);

  return (
    <button
      type="button"
      title={url}
      aria-label={expanded ? COPY.url_show_short : COPY.url_show_full}
      data-testid="user-url-bubble"
      onClick={() => setExpanded((value) => !value)}
      data-expanded={expanded ? "true" : "false"}
      className="max-w-full text-left break-all font-inherit"
    >
      {display}
    </button>
  );
}

function renderMessageContent(message: ChatMessage) {
  if (message.role === "agent") {
    return <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>;
  }
  const text = message.content.trim();
  if (/^https?:\/\//.test(text) && text.length > 50) {
    return <UserUrlBubble url={text} />;
  }
  return message.content;
}

export function MessagesOverlay({
  messages,
  streaming,
  onClose,
}: {
  messages: ChatMessage[];
  streaming: string;
  onClose: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages, streaming]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-x-0 bottom-[168px] z-40 px-4 md:left-[280px] md:px-6"
      data-testid="messages-overlay"
      onMouseDown={onClose}
    >
      <div
        className="mx-auto max-h-[40vh] max-w-[920px] overflow-y-auto rounded-2xl border border-stone-200/80 dark:border-stone-800/80 bg-stone-50/95 dark:bg-stone-900/95 p-4 shadow-[0_18px_60px_-24px_rgba(28,25,23,0.45)] backdrop-blur-sm"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <span className="font-serif-cn text-sm text-stone-900 dark:text-stone-50">
            {COPY.messages_overlay_title}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-stone-500 dark:text-stone-400 hover:text-[#7c2d12] dark:hover:text-[#ea580c] transition-colors font-inherit"
          >
            {COPY.messages_overlay_close}
          </button>
        </div>
        <div className="flex flex-col gap-3">
          {messages.map((message, index) => (
            <div
              key={index}
              data-testid={message.role === "user" ? "chat-user-bubble" : undefined}
              className={
                message.role === "user"
                  ? "self-end max-w-[85%] rounded-2xl rounded-br-sm bg-stone-900 dark:bg-[#7c2d12] px-3.5 py-2.5 text-[13px] leading-[1.55] text-[#faf8f3] overflow-hidden"
                  : "agent-msg self-start max-w-[85%] rounded-2xl rounded-bl-sm border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-4 py-3 text-[13px] leading-[1.65] text-stone-900 dark:text-stone-100 break-words"
              }
            >
              {renderMessageContent(message)}
            </div>
          ))}
          {streaming && (
            <div className="agent-msg self-start max-w-[85%] rounded-2xl rounded-bl-sm border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-4 py-3 text-[13px] leading-[1.65] text-stone-900 dark:text-stone-100">
              <Markdown remarkPlugins={[remarkGfm]}>{streaming}</Markdown>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
