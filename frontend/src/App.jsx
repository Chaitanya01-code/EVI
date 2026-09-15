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
  const audioRef = useRef(null);
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

  const playVoiceResponse = async audioSource => {
    if (!audioSource) return;
    audioRef.current?.pause();
    const audio = new Audio(audioSource);
    audioRef.current = audio;
    try {
      await audio.play();
    } catch {
      setError('Voice response is ready, but audio playback was blocked.');
    }
  };

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
        setAssistantResponse(message.processing.text || message.processing.response);
        if (message.processing.tts_error) setError(message.processing.tts_error);
        if (message.processing.response_type === 'voice') {
          void playVoiceResponse(message.processing.audio);
        }
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
      setAssistantResponse(result.text || result.response);
      if (result.response_type === 'voice') {
        void playVoiceResponse(result.audio);
      }
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
            {error ? <div className="transcript-error">{error}</div> : (
              <>
                {transcript && (
                  <div className="message-row message-user">
                    <span className="message-label">You</span>
                    <span>{transcript}</span>
                  </div>
                )}
                {interimTranscript && (
                  <div className="message-row message-interim">
                    <span className="message-label">Listening</span>
                    <span>{interimTranscript}</span>
                  </div>
                )}
                {assistantResponse && (
                  <div className="message-row message-assistant">
                    <span className="message-label">EVI</span>
                    <span>{assistantResponse}</span>
                  </div>
                )}
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

        {/* Footer */}
        <footer className="evi-footer">
          Ready when you are&nbsp;<span className="footer-heart">🧡</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
