import {
  Check,
  LogOut,
  MessageSquareText,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";

import type { Conversation, User } from "../../types/api";

type ConversationSidebarProps = {
  open: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
  user: User | null;
  loading: boolean;
  busy: boolean;
  onToggle: () => void;
  onNew: () => void;
  onSelect: (conversationId: string) => void;
  onRename: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onLogout: () => void;
};

// ConversationSidebar provides history navigation and collapses to an icon rail on desktop.
export function ConversationSidebar({
  open,
  conversations,
  activeConversationId,
  user,
  loading,
  busy,
  onToggle,
  onNew,
  onSelect,
  onRename,
  onDelete,
  onLogout,
}: ConversationSidebarProps) {
  const displayName = user?.display_name || user?.email || "Account";

  return (
    <>
      {open ? (
        <button
          aria-label="Close conversation sidebar"
          className="fixed inset-0 z-40 bg-[#2c211b]/25 backdrop-blur-[2px] lg:hidden"
          onClick={onToggle}
          type="button"
        />
      ) : null}

      <aside
        className={`fixed bottom-0 left-0 top-[104px] z-50 flex w-[286px] shrink-0 flex-col border-r border-[#99775c]/20 bg-[#eae7dd]/94 shadow-2xl backdrop-blur-2xl transition-[width,transform] duration-300 lg:relative lg:bottom-auto lg:top-auto lg:z-30 lg:h-full lg:translate-x-0 lg:shadow-none ${
          open
            ? "translate-x-0 lg:w-[286px]"
            : "-translate-x-full lg:w-[72px]"
        }`}
      >
        <div className={`border-b border-[#99775c]/15 ${open ? "p-3" : "p-2"}`}>
          <button
            aria-label="Create new conversation"
            className={`flex h-11 items-center justify-center bg-[#99775c] font-semibold text-white shadow-sm transition hover:bg-[#806047] disabled:cursor-not-allowed disabled:opacity-55 ${open ? "w-full gap-2 rounded-xl px-4 text-sm" : "w-11 rounded-full"}`}
            disabled={busy}
            onClick={onNew}
            title="New conversation"
            type="button"
          >
            <Plus size={18} />
            {open ? <span>New conversation</span> : null}
          </button>
        </div>

        <nav aria-label="Conversation history" className={`chat-scrollbar flex-1 overflow-y-auto ${open ? "p-3" : "px-2 py-3"}`}>
          {loading && open ? (
            <div className="space-y-2 px-1" aria-label="Loading conversations">
              {[0, 1, 2].map((item) => (
                <div className="h-12 animate-pulse rounded-lg bg-white/35" key={item} />
              ))}
            </div>
          ) : null}

          {!loading && conversations.length === 0 && open ? (
            <p className="px-2 py-5 text-sm leading-6 text-[#806d60]">No conversations yet.</p>
          ) : null}

          <div className="space-y-1">
            {conversations.map((conversation) => {
              const active = conversation.id === activeConversationId;
              return (
                <div
                  className={`group relative flex items-center transition ${
                    open ? "rounded-xl" : "justify-center rounded-full"
                  } ${active ? "bg-white/62 text-[#3f3028] shadow-sm" : "text-[#695548] hover:bg-white/35"}`}
                  key={conversation.id}
                >
                  <button
                    aria-current={active ? "page" : undefined}
                    className={`flex min-w-0 items-center ${open ? "h-[54px] flex-1 gap-3 px-3 pr-16 text-left" : "h-11 w-11 justify-center"}`}
                    onClick={() => onSelect(conversation.id)}
                    title={conversation.title}
                    type="button"
                  >
                    <MessageSquareText className="shrink-0 text-[#99775c]" size={17} />
                    {open ? (
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold">{conversation.title}</span>
                        <span className="mt-0.5 block truncate text-[11px] text-[#8a7567]">
                          {conversation.last_message_preview || "Empty conversation"}
                        </span>
                      </span>
                    ) : null}
                  </button>

                  {open ? (
                    <div className={`absolute right-2 flex items-center gap-0.5 ${active ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                      <button
                        aria-label={`Rename ${conversation.title}`}
                        className="flex h-7 w-7 items-center justify-center rounded-full text-[#806957] hover:bg-[#eae7dd]"
                        onClick={() => onRename(conversation)}
                        title="Rename conversation"
                        type="button"
                      >
                        <Pencil size={13} />
                      </button>
                      <button
                        aria-label={`Delete ${conversation.title}`}
                        className="flex h-7 w-7 items-center justify-center rounded-full text-[#936052] hover:bg-[#f0dcd4]"
                        onClick={() => onDelete(conversation)}
                        title="Delete conversation"
                        type="button"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </nav>

        <div className={`border-t border-[#99775c]/15 ${open ? "p-3" : "p-2"}`}>
          <div className={`flex items-center ${open ? "gap-3 rounded-xl px-2 py-1.5" : "justify-center"}`}>
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#344b52] text-xs font-bold uppercase text-white">
              {displayName.slice(0, 2)}
            </span>
            {open ? (
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-[#4d3b30]">{displayName}</p>
                <p className="mt-0.5 flex items-center gap-1 text-[10px] text-[#7f6a5b]">
                  <Check size={11} /> Signed in
                </p>
              </div>
            ) : null}
            <button
              aria-label="Log out"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[#765a46] transition hover:bg-white/50"
              onClick={onLogout}
              title="Log out"
              type="button"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
