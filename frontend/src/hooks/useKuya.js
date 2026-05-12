import { useConversation } from "@elevenlabs/react";

export function useKuya(agentId) {
  const conversation = useConversation({ agentId });
  return conversation;
}
