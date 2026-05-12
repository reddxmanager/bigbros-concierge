export default function BookingConfirmation({ booking, isActive }) {
  if (!booking) {
    return null;
  }

  return (
    <section data-active={isActive}>
      <h2>Booking Confirmation</h2>
      <pre>{JSON.stringify(booking, null, 2)}</pre>
    </section>
  );
}
