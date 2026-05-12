export default function RoomsSection({ rooms, isActive }) {
  if (!rooms?.length) {
    return null;
  }

  return (
    <section data-active={isActive}>
      <h2>Available Rooms</h2>
      {rooms.map((room, idx) => (
        <article key={`${room.room_type ?? "room"}-${idx}`}>
          <h3>{room.room_type ?? room.type ?? "Room"}</h3>
          <p>Rate: {room.nightly_rate ?? room.rate ?? "TBD"} PHP</p>
        </article>
      ))}
    </section>
  );
}
