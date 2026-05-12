export default function CalendarSection({ highlights, isActive }) {
  if (!highlights) {
    return null;
  }

  return (
    <section data-active={isActive}>
      <h2>Availability Calendar</h2>
      <pre>{JSON.stringify(highlights, null, 2)}</pre>
    </section>
  );
}
