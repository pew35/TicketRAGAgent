import { Check, Copy, Database, UserRound } from "lucide-react";
import { useState } from "react";

import type { StreamEventData } from "../../services/chat";
import type { ChatMessage } from "../../types/api";

type MessageBubbleProps = {
  message: ChatMessage;
  streaming?: boolean;
  sources?: StreamEventData[];
};

// MessageBubble presents each exchange as a directional comic-style speech bubble.
export function MessageBubble({ message, streaming = false, sources = [] }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const assistant = message.role === "assistant";
  const failed = message.status === "failed";

  async function copyMessage() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <article className={`flex w-full gap-3 ${assistant ? "justify-start" : "justify-end"}`}>
      {assistant ? (
        <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#344b52] text-white shadow-sm">
          <Database size={16} />
        </span>
      ) : null}

      <div className={`group relative max-w-[82%] sm:max-w-[74%] ${assistant ? "order-none" : "order-first"}`}>
        <div
          className={`relative px-5 py-4 shadow-[0_12px_35px_rgba(63,48,40,0.1)] ${
            assistant
              ? `rounded-[22px] rounded-tl-md border bg-[#f7f4ee]/72 text-[#3f3028] backdrop-blur-xl ${failed ? "border-[#b06b5a]/45" : "border-white/60"}`
              : "rounded-[22px] rounded-tr-md border border-white/45 bg-[#d7c2ae]/82 text-[#3f3028] backdrop-blur-xl"
          }`}
        >
          <span
            className={`absolute top-3 h-4 w-4 rotate-45 ${
              assistant
                ? "-left-2 border-b border-l border-white/60 bg-[#f7f4ee]/90"
                : "-right-2 bg-[#d7c2ae]/90"
            }`}
          />
          <p className={`mb-1.5 text-[11px] font-semibold ${assistant ? "text-[#8b6b54]" : "text-[#6d513f]"}`}>
            {assistant ? "Ticket RAG Agent" : "You"}
          </p>
          <div className="whitespace-pre-wrap break-words text-[14px] leading-6">
            {message.content || (streaming ? <TypingDots /> : null)}
            {streaming && message.content ? <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-[#99775c] align-middle" /> : null}
          </div>

          {assistant && sources.length > 0 ? <SourceReferences sources={sources} /> : null}

          {assistant && message.content ? (
            <button
              aria-label="Copy answer"
              className="absolute -bottom-9 left-1 flex h-8 w-8 items-center justify-center rounded-full text-[#806b5d] opacity-0 transition hover:bg-white/55 group-hover:opacity-100 focus:opacity-100"
              onClick={copyMessage}
              title="Copy answer"
              type="button"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          ) : null}
        </div>
      </div>

      {!assistant ? (
        <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#eae7dd] text-[#765a46] shadow-sm ring-1 ring-[#99775c]/20">
          <UserRound size={16} />
        </span>
      ) : null}
    </article>
  );
}

function TypingDots() {
  return (
    <span aria-label="Agent is responding" className="inline-flex items-center gap-1 py-1">
      {[0, 1, 2].map((dot) => (
        <span
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#99775c]"
          key={dot}
          style={{ animationDelay: `${dot * 120}ms` }}
        />
      ))}
    </span>
  );
}

function SourceReferences({ sources }: { sources: StreamEventData[] }) {
  return (
    <details className="mt-4 border-t border-[#99775c]/15 pt-3">
      <summary className="cursor-pointer text-xs font-semibold text-[#765a46]">
        {sources.length} historical ticket{sources.length === 1 ? "" : "s"} consulted
      </summary>
      <div className="mt-3 space-y-2">
        {sources.map((source, index) => (
          <div className="border-l-2 border-[#99775c]/35 pl-3 text-xs leading-5 text-[#6c594c]" key={String(source.ticket_id ?? index)}>
            <p className="font-semibold text-[#4f3d32]">
              {String(source.ticket_id || `Source ${index + 1}`)} · {String(source.issue_type || "Support case")}
            </p>
            {typeof source.similarity === "number" ? (
              <p>Similarity {Math.round(source.similarity * 100)}%</p>
            ) : null}
          </div>
        ))}
      </div>
    </details>
  );
}
