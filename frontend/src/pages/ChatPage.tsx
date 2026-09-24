import {
  AlertCircle,
  LoaderCircle,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  SearchCheck,
  Send,
  Square,
} from "lucide-react";
import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import { ChatAgentStage } from "../components/chat/ChatAgentStage";
import { ConversationSidebar } from "../components/chat/ConversationSidebar";
import { MessageBubble } from "../components/chat/MessageBubble";
import { SceneBackground } from "../components/layout/SceneBackground";
import { useAuth } from "../hooks/useAuth";
import { useConversations } from "../hooks/useConversations";
import { sendMessageStream, type StreamEventData } from "../services/chat";
import type { ChatMessage, Conversation } from "../types/api";
import { extractErrorMessage } from "../utils/response";

const DEFAULT_AGENT_STATUS = "Ready to search historical tickets for a grounded answer.";

// ChatPage connects conversation history, streaming agent events, and the comic dialogue UI.
export function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 1024);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [agentStatus, setAgentStatus] = useState(DEFAULT_AGENT_STATUS);
  const [streamSources, setStreamSources] = useState<StreamEventData[]>([]);
  const [streamAssistantId, setStreamAssistantId] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const selectedConversationRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const { user, logout } = useAuth();
  const {
    conversations,
    conversation,
    isListLoading,
    isConversationLoading,
    listError,
    conversationError,
    createConversation,
    deleteConversation,
    updateTitle,
    refreshConversation,
    isCreating,
    isDeleting,
  } = useConversations(activeConversationId);

  useEffect(() => {
    if (!activeConversationId && conversations.length > 0) {
      selectConversation(conversations[0].id);
    }
  }, [activeConversationId, conversations]);

  useEffect(() => {
    if (conversation && !streaming) {
      setMessages(conversation.messages);
    }
  }, [conversation, streaming]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: streaming ? "auto" : "smooth" });
  }, [messages, agentStatus, streaming]);

  useEffect(() => () => abortControllerRef.current?.abort(), []);

  function selectConversation(conversationId: string) {
    if (conversationId === selectedConversationRef.current) {
      if (window.innerWidth < 1024) setSidebarOpen(false);
      return;
    }

    abortControllerRef.current?.abort();
    selectedConversationRef.current = conversationId;
    setActiveConversationId(conversationId);
    setMessages([]);
    setStreaming(false);
    setStreamSources([]);
    setStreamAssistantId(null);
    setAgentStatus(DEFAULT_AGENT_STATUS);
    setPageError(null);
    if (window.innerWidth < 1024) setSidebarOpen(false);
  }

  async function handleNewConversation() {
    try {
      setPageError(null);
      const created = await createConversation({});
      selectConversation(created.id);
    } catch (error) {
      setPageError(extractErrorMessage(error));
    }
  }

  async function handleDeleteConversation(target: Conversation) {
    if (!window.confirm(`Delete “${target.title}”?`)) return;

    try {
      await deleteConversation(target.id);
      if (target.id === selectedConversationRef.current) {
        const nextConversation = conversations.find((item) => item.id !== target.id);
        selectedConversationRef.current = nextConversation?.id ?? null;
        setActiveConversationId(nextConversation?.id ?? null);
        setMessages([]);
      }
    } catch (error) {
      setPageError(extractErrorMessage(error));
    }
  }

  async function handleRenameConversation(target: Conversation) {
    const title = window.prompt("Conversation title", target.title)?.trim();
    if (!title || title === target.title) return;

    try {
      await updateTitle({ conversationId: target.id, title });
    } catch (error) {
      setPageError(extractErrorMessage(error));
    }
  }

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    const question = draft.trim();
    if (!question || streaming) return;

    setPageError(null);
    let conversationId = selectedConversationRef.current;

    try {
      if (!conversationId) {
        const created = await createConversation({});
        conversationId = created.id;
        selectedConversationRef.current = conversationId;
        setActiveConversationId(conversationId);
      }

      const now = new Date().toISOString();
      const userMessageId = `local-user-${crypto.randomUUID()}`;
      const assistantMessageId = `local-assistant-${crypto.randomUUID()}`;
      const nextSequence = messages.length + 1;

      const optimisticUserMessage: ChatMessage = {
        id: userMessageId,
        conversation_id: conversationId,
        role: "user",
        status: "completed",
        sequence: nextSequence,
        content: question,
        created_at: now,
        updated_at: now,
      };
      const optimisticAssistantMessage: ChatMessage = {
        id: assistantMessageId,
        conversation_id: conversationId,
        role: "assistant",
        status: "pending",
        sequence: nextSequence + 1,
        content: "",
        created_at: now,
        updated_at: now,
      };

      setMessages((current) => [...current, optimisticUserMessage, optimisticAssistantMessage]);
      setDraft("");
      setStreaming(true);
      setStreamSources([]);
      setStreamAssistantId(assistantMessageId);
      setAgentStatus("Thinking...");

      const controller = new AbortController();
      abortControllerRef.current = controller;

      await sendMessageStream(
        { conversation_id: conversationId, content: question },
        {
          onStatus: (streamEvent) => setAgentStatus(streamEvent.content),
          onSources: (sources) => {
            setStreamSources(sources);
            setAgentStatus(`Found ${sources.length} relevant historical tickets.`);
          },
          onToken: (token) => {
            setMessages((current) => current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: message.content + token }
                : message,
            ));
          },
          onDone: (streamEvent) => {
            const elapsed = streamEvent.data?.elapsed_ms;
            setAgentStatus(
              typeof elapsed === "number"
                ? `Answer completed in ${(elapsed / 1000).toFixed(1)} seconds.`
                : streamEvent.content,
            );
            setMessages((current) => current.map((message) =>
              message.id === assistantMessageId && !message.content
                ? { ...message, content: streamEvent.content }
                : message,
            ));
          },
          onStored: () => setAgentStatus("Conversation saved."),
          onError: (error) => {
            setAgentStatus("I could not complete that answer.");
            setMessages((current) => current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, status: "failed", content: error.message }
                : message,
            ));
          },
        },
        { signal: controller.signal },
      );

      const updated = await refreshConversation(conversationId);
      if (selectedConversationRef.current === conversationId) {
        setMessages(updated.messages);
      }
    } catch (error) {
      setPageError(extractErrorMessage(error));
    } finally {
      abortControllerRef.current = null;
      setStreaming(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  function stopStreaming() {
    abortControllerRef.current?.abort();
    setStreaming(false);
    setAgentStatus("Response stopped.");
  }

  const activeConversation = conversations.find(
    (item) => item.id === activeConversationId,
  );
  const visibleError = pageError ||
    (listError ? extractErrorMessage(listError) : null) ||
    (conversationError ? extractErrorMessage(conversationError) : null);
  const visibleAgentStatus = !streaming && messages.length > 0
    ? "Conversation saved."
    : agentStatus;

  return (
    <main className="relative flex h-screen min-w-0 overflow-hidden bg-[#eae7dd] pt-[104px] text-[#3f3028]">
      <SceneBackground />
      <header className="absolute inset-x-0 top-0 z-[60] flex h-[104px] border-b border-white/45 bg-[#eae7dd]/78 shadow-[0_10px_35px_rgba(63,48,40,0.08)] backdrop-blur-xl">
        <div
          className={`hidden h-full shrink-0 items-center border-r border-[#99775c]/18 transition-[width] duration-300 lg:flex ${
            sidebarOpen ? "w-[286px] justify-between px-5" : "w-[72px] justify-center"
          }`}
        >
          {sidebarOpen ? (
            <div className="min-w-0">
              <p className="truncate text-[17px] font-bold leading-none text-[#3f3028]">Ticket RAG</p>
              <p className="mt-1.5 text-[11px] font-medium text-[#806d60]">
                Support Desk
              </p>
            </div>
          ) : null}
          <button
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#765a46] transition hover:bg-white/45 hover:text-[#3f3028]"
            onClick={() => setSidebarOpen((open) => !open)}
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            type="button"
          >
            {sidebarOpen ? <PanelLeftClose size={19} /> : <PanelLeftOpen size={19} />}
          </button>
        </div>

        <div className="flex min-w-0 flex-1 items-center gap-3 px-4 sm:px-6 lg:px-8">
          <button
            aria-label="Toggle conversation sidebar"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#765a46] transition hover:bg-white/45 lg:hidden"
            onClick={() => setSidebarOpen((open) => !open)}
            title="Conversations"
            type="button"
          >
            <Menu size={20} />
          </button>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-[#806d60]">
              Conversation
            </p>
            <h1 className="mt-1 truncate text-xl font-semibold leading-tight text-[#3f3028] sm:text-[22px]">
              {activeConversation?.title || "New conversation"}
            </h1>
            <p className="mt-1 truncate text-xs text-[#806d60]">
              Grounded in historical support tickets
            </p>
          </div>
          {activeConversation ? (
            <button
              aria-label="Rename current conversation"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#765a46] transition hover:bg-white/45"
              onClick={() => handleRenameConversation(activeConversation)}
              title="Rename conversation"
              type="button"
            >
              <Pencil size={16} />
            </button>
          ) : null}
        </div>
      </header>

      <ConversationSidebar
        activeConversationId={activeConversationId}
        busy={isCreating || isDeleting || streaming}
        conversations={conversations}
        loading={isListLoading}
        onDelete={handleDeleteConversation}
        onLogout={logout}
        onNew={handleNewConversation}
        onRename={handleRenameConversation}
        onSelect={selectConversation}
        onToggle={() => setSidebarOpen((open) => !open)}
        open={sidebarOpen}
        user={user}
      />

      <ChatAgentStage />

      <section className="relative z-20 mb-[clamp(280px,30vh,380px)] flex min-w-0 flex-1 flex-col bg-transparent">
        <div className="chat-scrollbar min-h-0 flex-1 overflow-y-auto px-4 pb-5 pt-7 sm:px-7">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-7 pb-2">
            {visibleError ? (
              <div className="flex items-start gap-3 rounded-[16px] border border-white/55 border-l-2 border-l-[#a95f4f] bg-[#f7e9e4]/72 px-4 py-3 text-sm text-[#754438] shadow-sm backdrop-blur-xl">
                <AlertCircle className="mt-0.5 shrink-0" size={17} />
                <span>{visibleError}</span>
              </div>
            ) : null}

            {isConversationLoading ? (
              <div className="flex items-center justify-center gap-2 py-20 text-sm text-[#806d60]">
                <LoaderCircle className="animate-spin" size={18} /> Loading conversation
              </div>
            ) : null}

            {!isConversationLoading && messages.length === 0 ? (
              <div className="flex min-h-[48vh] items-center">
                <div className="relative max-w-lg rounded-[26px] rounded-bl-md border border-white/60 bg-[#eae7dd]/68 px-7 py-6 shadow-[0_22px_60px_rgba(63,48,40,0.14)] backdrop-blur-xl">
                  <span className="absolute -left-2 bottom-5 h-4 w-4 rotate-45 border-b border-l border-white/60 bg-[#eae7dd]/90" />
                  <p className="text-xs font-semibold text-[#8b6b54]">Ticket RAG Agent</p>
                  <h1 className="mt-2 text-2xl font-semibold leading-tight text-[#3f3028]">
                    What can I help you resolve?
                  </h1>
                  <p className="mt-3 text-sm leading-7 text-[#675347]">
                    Ask about a return, delivery delay, refund, replacement, or another customer issue.
                  </p>
                </div>
              </div>
            ) : null}

            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                sources={message.id === streamAssistantId ? streamSources : []}
                streaming={streaming && message.id === streamAssistantId}
              />
            ))}
            {messages.length > 0 || streaming ? (
              <div className="flex items-center gap-3 self-start rounded-[16px] border border-white/55 bg-[#f7f4ee]/62 px-4 py-3 text-[#6f5b4e] shadow-[0_12px_30px_rgba(63,48,40,0.08)] backdrop-blur-xl">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#e5ddd3]/80 text-[#765a46]">
                  {streaming ? <LoaderCircle className="animate-spin" size={15} /> : <SearchCheck size={15} />}
                </span>
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-[#8b6b54]">
                    Support agent
                  </p>
                  <p className="mt-0.5 truncate text-xs font-medium">{visibleAgentStatus}</p>
                </div>
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <footer className="shrink-0 bg-transparent px-3 pb-7 pt-2 sm:px-6 sm:pb-8">
          <form
            className="mx-auto flex max-w-3xl items-end gap-2 rounded-[22px] border border-white/60 bg-[#f7f4ee]/72 p-2 shadow-[0_16px_45px_rgba(63,48,40,0.15)] backdrop-blur-xl focus-within:border-[#99775c]/55"
            onSubmit={handleSubmit}
          >
            <textarea
              aria-label="Message Ticket RAG Agent"
              className="chat-scrollbar max-h-36 min-h-[44px] min-w-0 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm leading-6 text-[#3f3028] outline-none placeholder:text-[#8c7869]"
              disabled={isCreating}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Ask a customer support question..."
              rows={1}
              value={draft}
            />
            {streaming ? (
              <button
                aria-label="Stop response"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#344b52] text-white transition hover:bg-[#293d43]"
                onClick={stopStreaming}
                title="Stop response"
                type="button"
              >
                <Square fill="currentColor" size={14} />
              </button>
            ) : (
              <button
                aria-label="Send message"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#99775c] text-white shadow-sm transition hover:bg-[#806047] disabled:cursor-not-allowed disabled:opacity-45"
                disabled={!draft.trim() || isCreating}
                title="Send message"
                type="submit"
              >
                <Send size={17} />
              </button>
            )}
          </form>
        </footer>
      </section>
    </main>
  );
}
