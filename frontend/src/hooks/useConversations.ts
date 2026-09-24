import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
  updateConversationTitle,
} from "../services/chat";
import type { Conversation, ConversationDetail } from "../types/api";

const conversationListKey = ["conversations"] as const;
const conversationDetailKey = (conversationId: string) => [
  "conversations",
  conversationId,
] as const;

// Group conversation queries and mutations so the page only manages interaction state.
export function useConversations(activeConversationId: string | null) {
  const queryClient = useQueryClient();

  const conversationsQuery = useQuery({
    queryKey: conversationListKey,
    queryFn: () => getConversations({ limit: 100 }),
  });

  const conversationQuery = useQuery({
    queryKey: activeConversationId
      ? conversationDetailKey(activeConversationId)
      : ["conversations", "none"],
    queryFn: () => getConversation(activeConversationId as string),
    enabled: Boolean(activeConversationId),
  });

  const createMutation = useMutation({
    mutationFn: createConversation,
    onSuccess: (conversation) => {
      queryClient.setQueryData<Conversation[]>(conversationListKey, (current = []) => [
        conversation,
        ...current.filter((item) => item.id !== conversation.id),
      ]);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData<Conversation[]>(conversationListKey, (current = []) =>
        current.filter((conversation) => conversation.id !== deletedId),
      );
      queryClient.removeQueries({ queryKey: conversationDetailKey(deletedId) });
    },
  });

  const titleMutation = useMutation({
    mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
      updateConversationTitle(conversationId, title),
    onSuccess: (updatedConversation) => {
      queryClient.setQueryData<Conversation[]>(conversationListKey, (current = []) =>
        current.map((conversation) =>
          conversation.id === updatedConversation.id ? updatedConversation : conversation,
        ),
      );
      queryClient.setQueryData<ConversationDetail>(
        conversationDetailKey(updatedConversation.id),
        (current) => current
          ? { ...current, conversation: updatedConversation }
          : current,
      );
    },
  });

  async function refreshConversation(conversationId: string): Promise<ConversationDetail> {
    const detail = await getConversation(conversationId);
    queryClient.setQueryData(conversationDetailKey(conversationId), detail);
    await queryClient.invalidateQueries({ queryKey: conversationListKey });
    return detail;
  }

  return {
    conversations: conversationsQuery.data ?? [],
    conversation: conversationQuery.data ?? null,
    isListLoading: conversationsQuery.isLoading,
    isConversationLoading: conversationQuery.isLoading,
    listError: conversationsQuery.error,
    conversationError: conversationQuery.error,
    createConversation: createMutation.mutateAsync,
    deleteConversation: deleteMutation.mutateAsync,
    updateTitle: titleMutation.mutateAsync,
    refreshConversation,
    isCreating: createMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
