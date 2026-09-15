function VoiceOutput({ response }) {
  if (!response) {
    return <div className="voice-output empty">No backend response yet.</div>;
  }

  return (
    <pre className="voice-output">
      {JSON.stringify(response, null, 2)}
    </pre>
  );
}

export default VoiceOutput;
