export default function BookingsList({ bookings }) {
  return (
    <section>
      <h2>Upcoming Bookings</h2>
      {bookings.length === 0 ? <p>No bookings yet.</p> : null}
      <ul>
        {bookings.map((booking, idx) => (
          <li key={idx}>{JSON.stringify(booking)}</li>
        ))}
      </ul>
    </section>
  );
}
