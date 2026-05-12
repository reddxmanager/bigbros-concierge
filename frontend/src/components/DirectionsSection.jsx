export default function DirectionsSection({ data, isActive }) {
  if (!data) {
    return null;
  }

  return (
    <section data-active={isActive}>
      <h2>Directions</h2>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </section>
  );
}
