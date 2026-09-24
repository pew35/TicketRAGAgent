// Shared TypeScript types that mirror backend business payloads.
export type RegisterRequest = {
  email: string;
  password: string;
  display_name?: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
};

export type User = {
  id: string;
  email: string;
  display_name?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  status: "pending" | "completed" | "failed";
  sequence: number;
  content: string;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = {
  conversation: Conversation;
  messages: ChatMessage[];
};

export type MessageAnswer = {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  answer: string;
  sources: Record<string, unknown>[];
  metadata: Record<string, unknown>;
};
