import { useState } from "react";
import KuyaOwner from "./KuyaOwner";
import BookingsList from "./BookingsList";

export default function App() {
  const [bookings, setBookings] = useState([]);

  return (
    <main>
      <h1>Kuya Owner Mode</h1>
      <KuyaOwner setBookings={setBookings} />
      <BookingsList bookings={bookings} />
    </main>
  );
}
