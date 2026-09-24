import { fetchEventSource, type EventSourceMessage } from "@microsoft/fetch-event-source";

import { useAuthStore } from "../stores/authStore";
import type {
  ChatMessage,
  Conversation,
  ConversationDetail,
  MessageAnswer,
} from "../types/api";
import { ErrorCode } from "../utils/errorCodes";
import {
  API_BASE_URL,
  refreshAccessToken,
} from "../utils/request";
import {
  ApiError,
  createApiError,
  isApiResponse,
  normalizeApiError,
  type ApiResponse,
} from "../utils/response";
import request from "../utils/request";

const CONVERSATIONS_PATH = "/api/conversations";

// Request body accepted when a new conversation is created.
export interface CreateConversationRequest {
  title?: string;
}

// A message request keeps the conversation id with its content for convenient UI calls.
export interface SendMessageRequest {
  conversation_id: string;
  content: string;
}

export interface ConversationQuery {
  limit?: number;
  offset?: number;
}

export type StreamEventType =
  | "status"
  | "thinking"
  | "sources"
  | "token"
  | "done"
  | "stored"
  | "error"
  | "message";

export type StreamEventData = Record<string, unknown>;

// StreamEvent is the normalized form of both agent events and server envelopes.
export interface StreamEvent {
  type: StreamEventType;
  code: number;
  content: string;
  data: StreamEventData | null;
}

export interface StoredMessageData {
  user_message_id: string;
  assistant_message_id: string;
}

// Callbacks let the chat page update progress, sources, tokens, and stored ids independently.
export interface StreamCallbacks {
  onEvent?: (event: StreamEvent) => void;
  onStatus?: (event: StreamEvent) => void;
  onThinking?: (event: StreamEvent) => void;
  onSources?: (sources: StreamEventData[], event: StreamEvent) => void;
  onToken?: (token: string, event: StreamEvent) => void;
  onDone?: (event: StreamEvent) => void;
  onStored?: (data: StoredMessageData, event: StreamEvent) => void;
  onError?: (error: ApiError) => void;
}

export interface StreamOptions {
  signal?: AbortSignal;
}

export function getConversations(
  query: ConversationQuery = {},
): Promise<Conversation[]> {
  return request.get<Conversation[]>(CONVERSATIONS_PATH, { params: query });
}

export function createConversation(
  data: CreateConversationRequest = {},
): Promise<Conversation> {
  return request.post<Conversation, CreateConversationRequest>(
    CONVERSATIONS_PATH,
    data,
  );
}

export function getConversation(
  conversationId: string,
  query: ConversationQuery = {},
): Promise<ConversationDetail> {
  return request.get<ConversationDetail>(
    conversationPath(conversationId),
    { params: query },
  );
}

export function getMessages(
  conversationId: string,
  query: ConversationQuery = {},
): Promise<ChatMessage[]> {
  return request.get<ChatMessage[]>(
    `${conversationPath(conversationId)}/messages`,
    { params: query },
  );
}

export function sendMessage(data: SendMessageRequest): Promise<MessageAnswer> {
  return request.post<MessageAnswer, { content: string }>(
    `${conversationPath(data.conversation_id)}/messages`,
    { content: data.content },
  );
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await request.delete<void>(conversationPath(conversationId));
}

export function updateConversationTitle(
  conversationId: string,
  title: string,
): Promise<Conversation> {
  return request.patch<Conversation, { title: string }>(
    conversationPath(conversationId),
    { title },
  );
}

// Stream one agent response. Callers can cancel it by passing an AbortController signal.
export async function sendMessageStream(
  data: SendMessageRequest,
  callbacks: StreamCallbacks = {},
  options: StreamOptions = {},
): Promise<void> {
  let hasRetriedAuthentication = false;

  try {
    while (true) {
      const accessToken = useAuthStore.getState().accessToken;
      if (!accessToken) {
        throw new ApiError({
          code: ErrorCode.AUTH_REQUIRED,
          message: "Authentication is required.",
          httpStatus: 401,
        });
      }

      try {
        await openMessageStream(
          data,
          accessToken,
          callbacks,
          options.signal,
        );
        return;
      } catch (error) {
        const apiError = normalizeApiError(error);
        const refreshToken = useAuthStore.getState().refreshToken;
        const canRefresh =
          apiError.httpStatus === 401 &&
          !hasRetriedAuthentication &&
          Boolean(refreshToken);

        if (!canRefresh) {
          throw apiError;
        }

        hasRetriedAuthentication = true;
        try {
          await refreshAccessToken();
        } catch (refreshError) {
          useAuthStore.getState().logout();
          if (typeof window !== "undefined") {
            window.location.replace(`${import.meta.env.BASE_URL}login`);
          }
          throw refreshError;
        }
      }
    }
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    const apiError = normalizeApiError(error);
    callbacks.onError?.(apiError);
    throw apiError;
  }
}

async function openMessageStream(
  data: SendMessageRequest,
  accessToken: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  await fetchEventSource(
    `${API_BASE_URL}${conversationPath(data.conversation_id)}/messages/stream`,
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content: data.content }),
      signal,
      openWhenHidden: true,
      async onopen(response) {
        if (!response.ok) {
          throw await streamResponseError(response);
        }
      },
      onmessage(message) {
        const event = parseStreamEvent(message);
        callbacks.onEvent?.(event);

        switch (event.type) {
          case "status":
            callbacks.onStatus?.(event);
            callbacks.onThinking?.(event);
            break;
          case "thinking":
            callbacks.onThinking?.(event);
            break;
          case "sources":
            callbacks.onSources?.(readSources(event.data), event);
            break;
          case "token":
            callbacks.onToken?.(event.content, event);
            break;
          case "done":
            callbacks.onDone?.(event);
            break;
          case "stored": {
            const storedData = readStoredMessageData(event.data);
            if (storedData) {
              callbacks.onStored?.(storedData, event);
            }
            break;
          }
          case "error":
            throw new ApiError({
              code: event.code,
              message: event.content || "The agent stream failed.",
              data: event.data,
            });
          default:
            break;
        }
      },
      onerror(error) {
        // Throwing prevents automatic reconnects that could create duplicate messages.
        throw error;
      },
    },
  );
}

function parseStreamEvent(message: EventSourceMessage): StreamEvent {
  let payload: unknown;

  try {
    payload = JSON.parse(message.data);
  } catch (error) {
    throw new ApiError({
      code: ErrorCode.AGENT_RESPONSE_PARSE_FAILED,
      message: "Failed to parse a streaming response event.",
      originalError: error,
    });
  }

  const type = streamEventType(message.event);
  if (isApiResponse(payload)) {
    return {
      type,
      code: payload.code,
      content: payload.message,
      data: asRecord(payload.data),
    };
  }

  if (!isRecord(payload)) {
    throw new ApiError({
      code: ErrorCode.AGENT_RESPONSE_PARSE_FAILED,
      message: "The streaming response event has an invalid format.",
      data: payload,
    });
  }

  return {
    type,
    code: typeof payload.code === "number" ? payload.code : ErrorCode.SUCCESS,
    content: typeof payload.content === "string" ? payload.content : "",
    data: asRecord(payload.data),
  };
}

async function streamResponseError(response: Response): Promise<ApiError> {
  let payload: unknown;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (isApiResponse(payload)) {
    return createApiError(payload, response.status);
  }

  if (isRecord(payload) && isApiResponse(payload.detail)) {
    return createApiError(payload.detail, response.status);
  }

  return new ApiError({
    code: response.status === 401
      ? ErrorCode.INVALID_ACCESS_TOKEN
      : ErrorCode.AGENT_STREAM_FAILED,
    message: response.statusText || "Failed to open the message stream.",
    httpStatus: response.status,
    data: payload,
  });
}

function conversationPath(conversationId: string): string {
  return `${CONVERSATIONS_PATH}/${encodeURIComponent(conversationId)}`;
}

function streamEventType(value: string): StreamEventType {
  const knownTypes: StreamEventType[] = [
    "status",
    "thinking",
    "sources",
    "token",
    "done",
    "stored",
    "error",
    "message",
  ];
  return knownTypes.includes(value as StreamEventType)
    ? value as StreamEventType
    : "message";
}

function readSources(data: StreamEventData | null): StreamEventData[] {
  const sources = data?.sources;
  return Array.isArray(sources) ? sources.filter(isRecord) : [];
}

function readStoredMessageData(
  data: StreamEventData | null,
): StoredMessageData | null {
  if (
    typeof data?.user_message_id !== "string" ||
    typeof data.assistant_message_id !== "string"
  ) {
    return null;
  }

  return {
    user_message_id: data.user_message_id,
    assistant_message_id: data.assistant_message_id,
  };
}

function asRecord(value: unknown): StreamEventData | null {
  return isRecord(value) ? value : null;
}

function isRecord(value: unknown): value is StreamEventData {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export type { ApiResponse };
