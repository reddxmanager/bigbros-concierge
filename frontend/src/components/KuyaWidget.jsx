export default function KuyaWidget() {
  const agentId = import.meta.env.VITE_ELEVENLABS_AGENT_ID;

  if (!agentId) {
    return <p>Set VITE_ELEVENLABS_AGENT_ID in .env</p>;
  }

  return <elevenlabs-convai agent-id={agentId}></elevenlabs-convai>;
}
