import KuyaWidget from "./KuyaWidget";

export default function TalkToKuyaSection() {
  return (
    <section className="talk-kuya" aria-labelledby="talk-kuya-heading">
      <h2 id="talk-kuya-heading">Talk to Kuya</h2>
      <p className="lead">
        Ask about the resort, rooms, or the area. Tap start and speak when the connection is ready; your browser will ask for microphone access.
      </p>
      <KuyaWidget />
    </section>
  );
}
