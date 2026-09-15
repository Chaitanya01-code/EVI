import { useEffect, useRef, useState } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function toPcm16(input, inputSampleRate) {
  const sampleRateRatio = inputSampleRate / 16000;
  const outputLength = Math.max(1, Math.round(input.length / sampleRateRatio));
  const output = new ArrayBuffer(outputLength * 2);
  const view = new DataView(output);

  for (let outputIndex = 0; outputIndex < outputLength; outputIndex += 1) {
    const inputIndex = Math.min(input.length - 1, Math.floor(outputIndex * sampleRateRatio));
    const sample = Math.max(-1, Math.min(1, input[inputIndex]));
    view.setInt16(outputIndex * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return output;
}

const MicIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/>
    <path d="M19 11a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 0 0-2 0 7 7 0 0 0 6 6.92V20H9a1 1 0 0 0 0 2h6a1 1 0 0 0 0-2h-2v-2.08A7 7 0 0 0 19 11z"/>
  </svg>
);

const VsCodeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M16.7 3L9 11.4 4.3 7.5 3 8.5l5 4-5 4L4.3 17.5 9 13.5l7.7 8.5 3.3-1.7V4.7z"/>
  </svg>
);

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <circle cx="11" cy="11" r="8"/>
    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const FileIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10 9 9 9 8 9"/>
  </svg>
);

const SettingsIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);

const LeafIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M11 20A7 7 0 0 1 4 13c0-7 7-12 15-12a9 9 0 0 1-8 19z"/>
    <path d="M4 13s2-1 4-1 4 1 4 1"/>
    <path d="M12 3s1 2 1 4-1 4-1 4"/>
  </svg>
);

const quickActions = [
  { id: 'vscode', icon: <VsCodeIcon />, label: 'Open VS Code' },
  { id: 'youtube', icon: <SearchIcon />, label: 'Search on YouTube' },
  { id: 'file', icon: <FileIcon />, label: 'Read this file' },
  { id: 'settings', icon: <SettingsIcon />, label: 'Open Settings' },
];

function App() {
  const [listening, setListening] = useState(false);
  const [pulseAnim, setPulseAnim] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('Connecting to EVI...');
  const [error, setError] = useState('');
  const [assistantResponse, setAssistantResponse] = useState('');
  const [textInput, setTextInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const socketRef = useRef(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioSourceRef = useRef(null);
  const processorRef = useRef(null);

  useEffect(() => {
    let active = true;

    fetch(`${API_BASE_URL}/`)
      .then(response => {
        if (!response.ok) throw new Error('Backend returned an error');
        return response.json();
      })
      .then(() => {
        if (active) setConnectionStatus('Ready');
      })
      .catch(() => {
        if (active) setConnectionStatus('Backend unavailable');
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => () => stopListening(), []);

  const stopListening = () => {
    processorRef.current?.disconnect();
    audioSourceRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach(track => track.stop());
    audioContextRef.current?.close();
    socketRef.current?.close();
    processorRef.current = null;
    audioSourceRef.current = null;
    mediaStreamRef.current = null;
    audioContextRef.current = null;
    socketRef.current = null;
    setListening(false);
  };

  const startListening = async () => {
    setError('');
    setInterimTranscript('');

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone access is not supported in this browser.');
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const websocketUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/api/voice/listen?session_id=${encodeURIComponent(sessionId)}`;
    const socket = new WebSocket(websocketUrl);
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    socket.onopen = () => {
      setListening(true);
      setConnectionStatus('Listening');
      source.connect(processor);
      processor.connect(audioContext.destination);
    };
    socket.onmessage = event => {
      const message = JSON.parse(event.data);
      if (message.error) {
        setError(message.error);
        stopListening();
      } else if (message.processing) {
        setProcessing(false);
        setAssistantResponse(message.processing.response);
        setConnectionStatus('Ready');
      } else if (message.is_final) {
        setTranscript(previous => `${previous} ${message.transcript}`.trim());
        setInterimTranscript('');
        setProcessing(true);
      } else {
        setInterimTranscript(message.transcript);
      }
    };
    socket.onerror = () => {
      setError('Could not connect to the voice service.');
      stopListening();
    };
    socket.onclose = () => {
      if (socketRef.current === socket) {
        setConnectionStatus('Ready');
        stopListening();
      }
    };
    processor.onaudioprocess = event => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(toPcm16(event.inputBuffer.getChannelData(0), audioContext.sampleRate));
      }
    };

    socketRef.current = socket;
    audioContextRef.current = audioContext;
    mediaStreamRef.current = stream;
    audioSourceRef.current = source;
    processorRef.current = processor;
  };

  const submitText = async event => {
    event.preventDefault();
    const message = textInput.trim();
    if (!message || processing) return;
    setError('');
    setProcessing(true);
    setTranscript(message);
    setInterimTranscript('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: message, session_id: sessionId, input_type: 'text' }),
      });
      if (!response.ok) throw new Error('Request failed');
      const result = await response.json();
      setAssistantResponse(result.response);
      setConnectionStatus('Ready');
      setTextInput('');
    } catch {
      setError('Could not process that request.');
    } finally {
      setProcessing(false);
    }
  };

  const toggleMic = async () => {
    setPulseAnim(true);
    setTimeout(() => setPulseAnim(false), 600);
    if (listening) {
      stopListening();
      setConnectionStatus('Ready');
      return;
    }

    try {
      await startListening();
    } catch (startError) {
      stopListening();
      setError(startError.name === 'NotAllowedError'
        ? 'Microphone permission was denied.'
        : 'Could not start the microphone.');
    }
  };

  return (
    <div className="evi-root">
      {/* ── Window title bar ── */}
      <div className="evi-titlebar">
        <div className="titlebar-brand">
          <span className="titlebar-leaf"><LeafIcon /></span>
          <span className="titlebar-name">EVI</span>
        </div>
        <div className="titlebar-controls">
          <button className="wc-btn wc-min" title="Minimize">
            <svg width="10" height="2" viewBox="0 0 10 2"><rect width="10" height="1.5" rx="0.75" fill="currentColor"/></svg>
          </button>
          <button className="wc-btn wc-max" title="Maximize">
            <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0.5" y="0.5" width="9" height="9" rx="1" fill="none" stroke="currentColor" strokeWidth="1.2"/></svg>
          </button>
          <button className="wc-btn wc-close" title="Close">
            <svg width="10" height="10" viewBox="0 0 10 10">
              <line x1="1" y1="1" x2="9" y2="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="9" y1="1" x2="1" y2="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      {/* ── Main content area ── */}
      <main className="evi-main">
        {/* Background wave decorations */}
        <div className="bg-wave bg-wave-1" />
        <div className="bg-wave bg-wave-2" />

        {/* Avatar section */}
        <div className="evi-avatar-section">
          <div className="avatar-sparkle avatar-sparkle-left">✦</div>
          <div className="avatar-wrapper">
            <img
              src="/evi_character.jpg"
              alt="EVI assistant character"
              className="evi-avatar"
              draggable="false"
            />
          </div>
          <div className="avatar-heart">♡</div>
        </div>

        {/* Greeting */}
        <div className="evi-greeting">
          <h1 className="evi-title">
            Hi, I'm <span className="evi-name">EVI</span>
          </h1>
          <p className="evi-subtitle">
            Your AI desktop assistant.&nbsp; I'm here to help you,
            <br />
            just say what you need or click the mic.
          </p>
        </div>

        <div className="connection-status" role="status">
          <span className={`status-dot ${connectionStatus === 'Listening' ? 'status-listening' : ''}`} />
          {connectionStatus}
        </div>

        {(transcript || interimTranscript || error) && (
          <div className="transcript" aria-live="polite">
            {error ? <span className="transcript-error">{error}</span> : (
              <>
                <span>{transcript} </span>
                <span className="transcript-interim">{interimTranscript}</span>
                {assistantResponse && <p className="assistant-response">{assistantResponse}</p>}
              </>
            )}
          </div>
        )}

        <form className="text-input-form" onSubmit={submitText}>
          <input
            value={textInput}
            onChange={event => setTextInput(event.target.value)}
            placeholder="Type a message to EVI"
            aria-label="Message EVI"
          />
          <button type="submit" disabled={processing || !textInput.trim()}>Send</button>
        </form>

        {/* Mic button */}
        <div className="mic-container">
          {listening && <div className="mic-ripple" />}
          <button
            id="mic-btn"
            className={`mic-btn ${listening ? 'mic-active' : ''} ${pulseAnim ? 'mic-pulse' : ''}`}
            onClick={toggleMic}
            title={listening ? 'Stop listening' : 'Start listening'}
            aria-label="Microphone"
          >
            <MicIcon />
          </button>
        </div>

        {/* Quick action buttons */}
        <div className="quick-actions">
          {quickActions.map(action => (
            <button key={action.id} id={`action-${action.id}`} className="qa-btn">
              <span className="qa-icon">{action.icon}</span>
              <span className="qa-label">{action.label}</span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <footer className="evi-footer">
          Ready when you are&nbsp;<span className="footer-heart">🧡</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
