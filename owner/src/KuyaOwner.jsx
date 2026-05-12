import { useConversation } from "@elevenlabs/react";

export default function KuyaOwner({ setBookings }) {
  const conversation = useConversation({
    agentId: import.meta.env.VITE_ELEVENLABS_OWNER_AGENT_ID,
  });

  const startOwnerSession = async () => {
    await conversation.startSession({
      clientTools: {
        render_bookings: async ({ bookings }) => {
          setBookings(bookings ?? []);
          return "Owner bookings rendered.";
        },
      },
    });
  };

  return <button onClick={startOwnerSession}>Talk to Kuya (Owner)</button>;
}
