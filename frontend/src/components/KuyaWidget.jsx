import { useState } from "react";
import { useConversation } from "@elevenlabs/react";

export default function KuyaWidget({
  setActiveSection,
  setCalendarHighlights,
  setAvailableRooms,
  setBookingConfirmation,
  setDirectionsData,
}) {
  const [error, setError] = useState("");

  const conversation = useConversation({
    agentId: import.meta.env.VITE_ELEVENLABS_AGENT_ID,
  });

  const startConversation = async () => {
    setError("");
    try {
      await conversation.startSession({
        clientTools: {
          highlight_dates: async ({ check_in, check_out, available_dates, unavailable_dates }) => {
            setCalendarHighlights({
              checkIn: check_in,
              checkOut: check_out,
              available: available_dates ?? [],
              unavailable: unavailable_dates ?? [],
            });
            setActiveSection("calendar");
            return "Calendar updated.";
          },
          show_rooms: async ({ rooms }) => {
            setAvailableRooms(rooms ?? []);
            setActiveSection("rooms");
            return "Rooms shown.";
          },
          show_booking_confirmation: async (payload) => {
            setBookingConfirmation(payload ?? null);
            setActiveSection("confirmation");
            return "Booking confirmation shown.";
          },
          show_directions: async ({ address, google_maps_link, directions, landmarks }) => {
            setDirectionsData({
              address,
              mapLink: google_maps_link,
              directions,
              landmarks,
            });
            setActiveSection("directions");
            return "Directions shown.";
          },
        },
      });
    } catch (e) {
      setError("Failed to start voice session.");
    }
  };

  return (
    <section>
      <button onClick={startConversation}>Talk to Kuya</button>
      {error ? <p>{error}</p> : null}
    </section>
  );
}
